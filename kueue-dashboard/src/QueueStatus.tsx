import { useQuery } from "@tanstack/react-query";
import {
  Background,
  BackgroundVariant,
  Edge,
  MarkerType,
  Node,
  ReactFlow,
} from "@xyflow/react";

const X_SPACING = 200;
const Y_SPACING = 200;

export default function QueueStatus() {
  const queues = useQuery({
    queryKey: ["user-queues"],
    queryFn: async () => {
      const resp = await fetch(
        `https://localhost:8002/apis/kueue.x-k8s.io/v1beta1/localqueues`
      );
      return resp.json();
    },
  });

  if (queues.isPending || queues.isError) {
    return <></>;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  // const queueList = queues.data.items.map((localQueue: any) => (
  //   <Queue
  //     key={localQueue.metadata.uid}
  //     namespace={localQueue.metadata.namespace}
  //     localQueue={localQueue.metadata.name}
  //     clusterQueue={localQueue.spec.clusterQueue}
  //   ></Queue>
  // ));

  const clusterQueues = new Set<string>(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    queues.data.items.map((localQueue: any) => localQueue.spec.clusterQueue)
  );

  const namespaces = new Set<string>(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    queues.data.items.map((localQueue: any) => localQueue.metadata.namespace)
  );

  let nodes: Node[] = [];

  // Namespace groups
  nodes = nodes.concat(
    [...namespaces].map((ns: string, idx: number) => ({
      id: "ns-" + ns,
      type: "group",
      data: { label: ns },
      position: { x: idx * 350, y: 0 },
      style: {
        height: 50,
        width:
          [...queues.data.items].filter((lq) => lq.metadata.namespace === ns)
            .length * 200,
      },
    }))
  );

  // Cluster Queues
  nodes = nodes.concat(
    [...clusterQueues].map((cq: string, idx: number) => ({
      id: cq,
      position: { x: X_SPACING * idx, y: Y_SPACING },
      data: {
        label: cq,
      },
    }))
  );

  // Local Queues
  nodes = nodes.concat(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    queues.data.items.map((localQueue: any) => ({
      id: localQueue.metadata.name,
      position: {
        x:
          5 +
          200 *
            [...queues.data.items]
              .filter(
                (lq) => lq.metadata.namespace === localQueue.metadata.namespace
              )
              .findIndex((lq) => lq === localQueue),
        y: 5,
      },
      data: {
        label: localQueue.metadata.name,
        clusterQueue: localQueue.spec.clusterQueue,
      },
      parentId: "ns-" + localQueue.metadata.namespace,
      extent: "parent",
      type: "input",
    }))
  );

  const edges: Edge[] = nodes.map((n: Node) => ({
    id: `${n.id}-${n.data.clusterQueue}`,
    source: n.id,
    target: n.data.clusterQueue as string,
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 24,
      height: 24,
    },
  }));

  console.debug(nodes);

  return (
    <>
      <h1>Local Queues</h1>
      <div style={{ width: "100vw", height: "40vh" }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          colorMode="system"
          fitView
          attributionPosition="top-right"
        >
          <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
        </ReactFlow>
      </div>

      {/* {queueList} */}
    </>
  );
}
