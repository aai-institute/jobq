import logging

from fastapi import APIRouter
from kubernetes import client
from sqlmodel import select

from jobq_server.db import Project, ProjectCreate, ProjectPublic
from jobq_server.dependencies import DBSessionDep, KubernetesDep, KueueDep
from jobq_server.utils.kueue import ClusterQueue, ClusterQueueSpec, LocalQueue

router = APIRouter()


@router.get("/")
async def list_projects(db: DBSessionDep):
    return db.exec(select(Project)).all()


@router.post("/", status_code=201)
async def create_project(
    project: ProjectCreate,
    db: DBSessionDep,
    k8s: KubernetesDep,
    kueue: KueueDep,
) -> ProjectPublic:
    # Create namespace if it doesn't exist
    ns, created = k8s.ensure_namespace(project.namespace)
    if created:
        logging.info(f"Created Kubernetes namespace {ns.metadata.name}")

    # Create cluster queue if it doesn't exist
    cluster_queue = kueue.get_cluster_queue(project.cluster_queue)
    if cluster_queue is None:
        default_spec = {
            "namespaceSelector": {},
            "preemption": {
                "reclaimWithinCohort": "Any",
                "borrowWithinCohort": {
                    "policy": "LowerPriority",
                    "maxPriorityThreshold": 100,
                },
                "withinClusterQueue": "LowerPriority",
            },
            "resourceGroups": [
                {
                    "coveredResources": ["cpu", "memory"],
                    "flavors": [
                        {
                            "name": "default-flavor",
                            "resources": [
                                {"name": "cpu", "nominalQuota": 4},
                                {"name": "memory", "nominalQuota": 6},
                            ],
                        }
                    ],
                }
            ],
        }
        cluster_queue = ClusterQueue(
            metadata=client.V1ObjectMeta(name=project.cluster_queue),
            spec=ClusterQueueSpec.model_validate(default_spec),
        )
        kueue.create_cluster_queue(cluster_queue)
        logging.info(f"Created cluster queue {project.cluster_queue!r}")

    # Create local queue if it doesn't exist
    local_queue = kueue.get_local_queue(project.local_queue, project.namespace)
    if local_queue is None:
        local_queue = LocalQueue(
            metadata=client.V1ObjectMeta(
                name=project.local_queue, namespace=project.namespace
            ),
            spec={"clusterQueue": project.cluster_queue},
        )

        kueue.create_local_queue(local_queue)
        logging.info(
            f"Created user queue {project.local_queue!r} in namespace {project.namespace!r}"
        )

    # TODO: Apply finalizers to Kubernetes resources to prevent deletion while the project exists

    db_obj = Project.model_validate(project)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
