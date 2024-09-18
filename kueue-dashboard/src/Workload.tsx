import k8s from "@kubernetes/client-node";
import { mdiDatabaseOutline, mdiMemory } from "@mdi/js";
import Icon from "@mdi/react";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import cn from "classnames";
import { DateTime } from "luxon";
import { OwnerRef } from "./Queue";
import "./Workload.css";

export default function Workload({
  name,
  namespace,
  submissionTime,
  active,
  ownerRef,
}: {
  namespace: string;
  name: string;
  submissionTime: Date;
  active: boolean;
  ownerRef: OwnerRef;
}) {
  const details = useQuery({
    queryKey: ["workload", namespace, name],
    queryFn: async () => {
      const resp = await axios.get(
        `https://localhost:8002/apis/kueue.x-k8s.io/v1beta1/namespaces/${namespace}/workloads/${name}`
      );
      return resp.data;
    },
  });

  const owner = useQuery({
    queryKey: [ownerRef.apiVersion, ownerRef.kind, namespace, ownerRef.name],
    queryFn: async () => {
      const resp = await axios.get<k8s.KubernetesObject>(
        `https://localhost:8002/apis/${
          ownerRef.apiVersion
        }/namespaces/${namespace}/${ownerRef.kind.toLowerCase()}s/${
          ownerRef.name
        }`
      );
      return resp.data;
    },
  });

  if (details.isPending || details.isError) {
    return <></>;
  }
  if (owner.isPending || owner.isError) {
    return <></>;
  }

  const limits =
    details.data.spec.podSets[0].template.spec.containers[0].resources.limits;

  const cpu = limits.cpu;
  const mem = limits.memory;

  console.debug(owner.data);
  const submitter = owner.data?.metadata?.labels?.["x-jobby.io/submitter"];

  return (
    <div className={cn("workload-container", active && "active")}>
      <div className="workload-name">{name}</div>
      <div className="workload-owner">
        {ownerRef.kind.toLowerCase()}s.{ownerRef.apiVersion}/{ownerRef.name}
      </div>
      <div className="workload-submission-time">
        submitted {DateTime.fromJSDate(submissionTime).toRelative()}
        {submitter && ` by ${submitter}`}
      </div>
      <div className="workload-details">
        {cpu} <Icon path={mdiMemory} size={1} />
        ,&nbsp;
        {mem} <Icon path={mdiDatabaseOutline} size={1} />
      </div>
    </div>
  );
}
