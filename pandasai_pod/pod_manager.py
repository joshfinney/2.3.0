import asyncio
import logging
import uuid
import yaml
from typing import Optional, Dict, Any
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)


class PodSandboxManager:
    """Kubernetes pod-based sandbox manager for secure Python code execution."""
    
    def __init__(self, namespace: str = "default", image: str = "pandasai-sandbox:latest"):
        self.namespace = namespace
        self.image = image
        self.session_id = str(uuid.uuid4())[:8]
        self.pod_name = f"python-sandbox-{self.session_id}"
        self.service_name = f"python-sandbox-{self.session_id}"
        
        # Initialize Kubernetes client
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        
        self.k8s_client = client.CoreV1Api()
        self.apps_client = client.AppsV1Api()
        
        self._pod_ip: Optional[str] = None
        self._started = False

    async def start_pod(self) -> Dict[str, Any]:
        """Start a new sandbox pod with security constraints."""
        if self._started:
            return {"status": "already_running", "pod_name": self.pod_name}
        
        try:
            # Create pod specification
            pod_spec = self._create_pod_spec()
            
            # Create the pod
            await asyncio.get_event_loop().run_in_executor(
                None, 
                self.k8s_client.create_namespaced_pod,
                self.namespace, pod_spec
            )
            
            # Wait for pod to be ready
            await self._wait_for_pod_ready()
            
            # Create service for communication
            service_spec = self._create_service_spec()
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.k8s_client.create_namespaced_service,
                self.namespace, service_spec
            )
            
            self._started = True
            logger.info(f"Pod {self.pod_name} started successfully")
            
            return {
                "status": "started",
                "pod_name": self.pod_name,
                "service_name": self.service_name,
                "session_id": self.session_id
            }
            
        except ApiException as e:
            logger.error(f"Failed to start pod: {e}")
            raise RuntimeError(f"Pod creation failed: {e}")

    async def stop_pod(self) -> Dict[str, Any]:
        """Stop and cleanup the sandbox pod."""
        if not self._started:
            return {"status": "not_running"}
        
        try:
            # Delete service first
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.k8s_client.delete_namespaced_service,
                    self.service_name, self.namespace
                )
            except ApiException as e:
                if e.status != 404:
                    logger.warning(f"Failed to delete service: {e}")
            
            # Delete pod
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.k8s_client.delete_namespaced_pod,
                self.pod_name, self.namespace
            )
            
            self._started = False
            logger.info(f"Pod {self.pod_name} stopped successfully")
            
            return {
                "status": "stopped",
                "pod_name": self.pod_name
            }
            
        except ApiException as e:
            logger.error(f"Failed to stop pod: {e}")
            raise RuntimeError(f"Pod deletion failed: {e}")

    async def execute_code(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute Python code in the sandbox pod."""
        if not self._started:
            raise RuntimeError("Pod is not running. Call start_pod() first.")
        
        try:
            # Send code execution request to pod API
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"http://{self.service_name}.{self.namespace}.svc.cluster.local:8080/execute"
                payload = {
                    "code": code,
                    "timeout": timeout,
                    "session_id": self.session_id
                }
                
                async with session.post(url, json=payload, timeout=timeout) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        raise RuntimeError(f"Code execution failed: {error_text}")
                        
        except asyncio.TimeoutError:
            logger.error(f"Code execution timed out after {timeout}s")
            # Force restart pod on timeout
            await self.restart_pod()
            raise RuntimeError("Code execution timed out, pod restarted")
        except Exception as e:
            logger.error(f"Code execution error: {e}")
            raise

    async def restart_pod(self) -> Dict[str, Any]:
        """Restart the sandbox pod (useful for cleanup after errors)."""
        logger.info(f"Restarting pod {self.pod_name}")
        await self.stop_pod()
        return await self.start_pod()

    async def get_pod_status(self) -> Dict[str, Any]:
        """Get current pod status and health."""
        try:
            pod = await asyncio.get_event_loop().run_in_executor(
                None,
                self.k8s_client.read_namespaced_pod,
                self.pod_name, self.namespace
            )
            
            return {
                "name": pod.metadata.name,
                "phase": pod.status.phase,
                "ready": self._is_pod_ready(pod),
                "restarts": pod.status.container_statuses[0].restart_count if pod.status.container_statuses else 0,
                "started_at": pod.status.start_time.isoformat() if pod.status.start_time else None
            }
        except ApiException as e:
            if e.status == 404:
                return {"status": "not_found"}
            raise

    def _create_pod_spec(self) -> client.V1Pod:
        """Create Kubernetes pod specification."""
        return client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=self.pod_name,
                labels={
                    "app": "python-sandbox",
                    "session": self.session_id,
                    "component": "code-executor"
                }
            ),
            spec=client.V1PodSpec(
                restart_policy="Never",
                security_context=client.V1PodSecurityContext(
                    run_as_non_root=True,
                    run_as_user=1000,
                    fs_group=1000
                ),
                containers=[
                    client.V1Container(
                        name="python-sandbox",
                        image=self.image,
                        resources=client.V1ResourceRequirements(
                            limits={"memory": "512Mi", "cpu": "500m", "ephemeral-storage": "1Gi"},
                            requests={"memory": "256Mi", "cpu": "250m"}
                        ),
                        security_context=client.V1SecurityContext(
                            allow_privilege_escalation=False,
                            read_only_root_filesystem=False,
                            capabilities=client.V1Capabilities(drop=["ALL"])
                        ),
                        env=[
                            client.V1EnvVar(name="PYTHONUNBUFFERED", value="1"),
                            client.V1EnvVar(name="SESSION_ID", value=self.session_id)
                        ],
                        volume_mounts=[
                            client.V1VolumeMount(name="temp-volume", mount_path="/tmp"),
                            client.V1VolumeMount(name="workspace", mount_path="/workspace")
                        ],
                        ports=[client.V1ContainerPort(container_port=8080, name="api")],
                        liveness_probe=client.V1Probe(
                            http_get=client.V1HTTPGetAction(path="/health", port=8080),
                            initial_delay_seconds=5,
                            period_seconds=10,
                            failure_threshold=3
                        ),
                        readiness_probe=client.V1Probe(
                            http_get=client.V1HTTPGetAction(path="/ready", port=8080),
                            initial_delay_seconds=2,
                            period_seconds=5
                        )
                    )
                ],
                volumes=[
                    client.V1Volume(
                        name="temp-volume",
                        empty_dir=client.V1EmptyDirVolumeSource(size_limit="100Mi")
                    ),
                    client.V1Volume(
                        name="workspace", 
                        empty_dir=client.V1EmptyDirVolumeSource(size_limit="500Mi")
                    )
                ],
                node_selector={"workload-type": "sandbox"},
                tolerations=[
                    client.V1Toleration(
                        key="sandbox",
                        operator="Equal", 
                        value="true",
                        effect="NoSchedule"
                    )
                ]
            )
        )

    def _create_service_spec(self) -> client.V1Service:
        """Create Kubernetes service specification."""
        return client.V1Service(
            metadata=client.V1ObjectMeta(
                name=self.service_name,
                labels={
                    "app": "python-sandbox",
                    "session": self.session_id
                }
            ),
            spec=client.V1ServiceSpec(
                selector={
                    "app": "python-sandbox",
                    "session": self.session_id
                },
                ports=[
                    client.V1ServicePort(port=8080, target_port=8080, name="api")
                ],
                type="ClusterIP"
            )
        )

    async def _wait_for_pod_ready(self, timeout: int = 60):
        """Wait for pod to be in ready state."""
        for _ in range(timeout):
            try:
                pod = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.k8s_client.read_namespaced_pod,
                    self.pod_name, self.namespace
                )
                
                if self._is_pod_ready(pod):
                    self._pod_ip = pod.status.pod_ip
                    return
                    
            except ApiException:
                pass
            
            await asyncio.sleep(1)
        
        raise RuntimeError(f"Pod {self.pod_name} failed to become ready within {timeout}s")

    def _is_pod_ready(self, pod: client.V1Pod) -> bool:
        """Check if pod is ready."""
        if not pod.status.conditions:
            return False
        
        for condition in pod.status.conditions:
            if condition.type == "Ready" and condition.status == "True":
                return True
        return False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_pod()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_pod()