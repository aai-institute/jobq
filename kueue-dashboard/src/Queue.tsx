import { useQuery } from "@tanstack/react-query";
import "./Queue.css";
import Workload from "./Workload";
import apiClient from "./lib/api-client";

export interface OwnerRef {
  apiVersion: string;
  kind: string;
  name: string;
  uid: string;
}

export interface WorkloadSummaryMetadata {
  name: string;
  namespace: string;
  creationTimestamp: string;
  ownerReferences: OwnerRef[];
}

export interface WorkloadSummaryItem {
  metadata: WorkloadSummaryMetadata;
  priority: number;
  localQueueName: string;
  positionInClusterQueue: number;
  positionInLocalQueue: number;
}

export interface PendingWorkloadsSummary {
  kind: string;
  apiVersion: string;
  metadata: { [key: string]: string };
  items: WorkloadSummaryItem[];
}

export default function Queue({
  namespace,
  localQueue,
  clusterQueue,
}: {
  namespace: string;
  localQueue: string;
  clusterQueue: string;
}) {
  const query = useQuery({
    queryKey: ["queue", clusterQueue],
    queryFn: async () => {
      const resp = await apiClient.get<PendingWorkloadsSummary>(
        `/visibility.kueue.x-k8s.io/v1alpha1/clusterqueues/${clusterQueue}/pendingworkloads`
      );
      return resp.data;
    },
    refetchInterval: 1000,
  });

  if (query.isPending || query.isError) {
    return <></>;
  }

  const queueData = (query.data as PendingWorkloadsSummary).items
    .filter(
      (item) =>
        item.metadata.namespace === namespace &&
        item.localQueueName === localQueue
    )
    .sort((item) => item.positionInLocalQueue);

  const items = queueData.map((item) => (
    <Workload
      key={item.metadata.name}
      namespace={item.metadata.namespace}
      name={item.metadata.name}
      submissionTime={new Date(item.metadata.creationTimestamp)}
      active={item.positionInClusterQueue === 0}
      ownerRef={item.metadata.ownerReferences[0]}
    ></Workload>
  ));

  return (
    <div className="queue">
      <div className="queue-name">
        {namespace}/{localQueue}
      </div>
      <div className="queue-items">{items}</div>
    </div>
  );
}
