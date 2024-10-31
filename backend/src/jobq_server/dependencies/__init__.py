from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import Session

from jobq_server.db import get_engine
from jobq_server.models import JobId
from jobq_server.services.k8s import KubernetesService
from jobq_server.utils.kueue import KueueWorkload


def k8s_service() -> KubernetesService:
    return KubernetesService()


def managed_workload(
    k8s: Annotated[KubernetesService, Depends(k8s_service)],
    uid: JobId,
    namespace: str | None = None,
) -> KueueWorkload:
    wl = k8s.workload_for_managed_resource(uid, namespace)
    if wl is None:
        raise HTTPException(404, "workload not found")
    return wl


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session


ManagedWorkload = Annotated[KueueWorkload, Depends(managed_workload)]
Kubernetes = Annotated[KubernetesService, Depends(k8s_service)]
DBSessionDep = Annotated[Session, Depends(get_session)]
