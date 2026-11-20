# Formal Kubernetes QA - human review sheet (T4)

Nothing in this file is a result. It records the two human steps that
`eval/metrics.py` deliberately refuses to fake: that each refusal item really
cannot be answered from the frozen snapshot, and that each answerable item's
question, gold quote and reference answer agree.

Corpus under review: `data/raw/frozen_manifest.json`, corpus_id
`cs5481-k8s-v135-16docs-36fd3eedf33f` (12 Kubernetes pages + 4 Wikipedia pages).
QA file: `eval/qa_set.csv`. The Wikipedia set in `eval/qa_set_dev_v0.csv` is
development material and is not covered by this sheet.

## 1. Refusal labels (needed before any abstention number is quotable)

For each row: open the named page, search for the tokens and for any other
wording of the question. If the corpus really cannot answer it, append
`REVIEWED_BY: <your name>` to that item's `notes` in `eval/qa_set.csv`, after
the `ABSENT_TOKENS:` list. If it can be answered, delete the row or rewrite it
as an answerable item - do not sign it.

| qid | question | pages to re-read | declared absent tokens |
| --- | --- | --- | --- |
| KN01 | Which cloud provider offers the cheapest managed Kubernetes cluster? | all 12 pages (spot-check for prices) | `cheapest; pricing; cost per hour` |
| KN02 | Who originally developed Kubernetes and in which year was it announced? | k8s_v135_components | `originally developed by; announced in 2014` |
| KN03 | Which programming language is kube-proxy written in? | k8s_v135_components, k8s_v135_services, k8s_v135_nodes | `programming language; written in` |
| KN04 | How do I install a Helm chart into a namespace? | k8s_v135_configmaps, k8s_v135_kubectl_quick_reference | `helm; chart` |
| KN05 | What uptime SLA does a highly-available control plane guarantee? | k8s_v135_components, k8s_v135_nodes | `sla; uptime percentage; guaranteed availability` |
| KN06 | What average latency, in milliseconds, should an httpGet readiness probe add? | k8s_v135_probes | `average latency; milliseconds` |
| KN07 | Is there a maximum number of replicas a single Deployment can have? | k8s_v135_deployments, k8s_v135_stateless_deployment | `maximum number of replicas; replica limit` |
| KN08 | Which minimum Linux kernel version is required for a v1.35 worker node? | k8s_v135_nodes, k8s_v135_components | `minimum kernel; kernel requirement; linux kernel version` |
| KN09 | Does Kubernetes ship NVIDIA GPU drivers for Windows Server nodes? | k8s_v135_pods, k8s_v135_nodes | `nvidia; gpu driver` |
| KN10 | What is the default password for the kubectl admin user? | k8s_v135_kubectl_quick_reference, k8s_v135_secrets | `default password; admin password` |

Each item's `notes` in the csv says why it is a refusal (OUT-OF-DOMAIN or
NEAR-MISS) and names the section a reader might mistake for an answer; start
there, then search the page yourself rather than trusting the note.

Machine check so far (`python -m eval.metrics validate --require-reviewed` fails
until every row above is signed): the declared tokens are confirmed absent as
whole words, which is a necessary condition only. Absence of a phrase is not
the same as absence of an answer.

## 2. Answerable items (needed before answer_correctness is graded)

Check for each row that (a) the gold quote is verbatim in the page, (b) the quote
actually answers the question, and (c) the reference answer adds nothing the quote
does not support. Ambiguous items should be rewritten, not graded around.

| qid | doc | line | question |
| --- | --- | --- | --- |
| K01 | `k8s_v135_components` | 7 | What are the two top-level parts that make up a Kubernetes cluster? |
| K02 | `k8s_v135_components` | 17-18 | Which control-plane component holds all API server data, and how is that component described? |
| K03 | `k8s_v135_components` | 36-37 | Which node component is responsible for the network rules that implement Services? |
| K04 | `k8s_v135_nodes` | 118 | What kubelet setting is needed if Node objects should be created by hand instead of registering themselves? |
| K05 | `k8s_v135_nodes` | 205 | How often does the node controller check the state of each node by default? |
| K06 | `k8s_v135_pods` | 25 | How is a Pod described in terms of its containers and what they share? |
| K07 | `k8s_v135_pods` | 418 | By default, when do init containers run relative to the app containers of a Pod? |
| K08 | `k8s_v135_deployments` | 258 | By default, how far above the desired number of Pods may a Deployment create Pods during a rollout? |
| K09 | `k8s_v135_deployments` | 345 | Can the label selector of an apps/v1 Deployment be edited after the Deployment exists? |
| K10 | `k8s_v135_services` | 15 | What does Kubernetes expect from network plugins regarding Pod IP addresses? |
| K11 | `k8s_v135_services` | 650 | Which values are allowed for .status.loadBalancer.ingress.ipMode? |
| K12 | `k8s_v135_configmaps` | 224 | A Pod reads a ConfigMap through environment variables. Does editing that ConfigMap change the running Pod? |
| K13 | `k8s_v135_configmaps` | 338 | How do you create an immutable ConfigMap? |
| K14 | `k8s_v135_secrets` | 109 | What is the Secret type field used for? |
| K15 | `k8s_v135_secrets` | 270 | Does the base64 encoding of a dockerconfigjson Secret's auth value protect it from readers? |
| K16 | `k8s_v135_probes` | 23 | What does the kubelet use startup probes for? |
| K17 | `k8s_v135_probes` | 583 | How much of the response body does the kubelet read when it runs an httpGet probe? |
| K18 | `k8s_v135_persistent_volumes` | 357 | What must a StorageClass declare before its PersistentVolumeClaims can be expanded? |
| K19 | `k8s_v135_persistent_volumes` | 545 | Which two volumeModes does Kubernetes support for PersistentVolumes? |
| K20 | `k8s_v135_persistent_volumes` | 609 | Do volume access modes stop another Pod from writing to a volume that is already mounted? |
| K21 | `k8s_v135_scheduling` | 314 | Which field of the Pod spec is used to configure inter-pod affinity? |
| K22 | `k8s_v135_scheduling` | 688 | Is a value set in nominatedNodeName guaranteed to decide where the Pod runs? |
| K23 | `k8s_v135_kubectl_quick_reference` | 49 | Which kubectl command shows the merged kubeconfig settings? |
| K24 | `k8s_v135_kubectl_quick_reference` | 164 | Which kubectl command lists all pods in all namespaces? |
| K25 | `k8s_v135_stateless_deployment` | 1 | What kind of object does the stateless application tutorial use to run an application? |
| K26 | `k8s_v135_stateless_deployment` | 22 | In the stateless application deployment tutorial, which Kubernetes server version is required and how is the version checked? |

## 3. Sign-off

- Reviewer name(s) and date: ______________________
- Items changed after review: ______________________
- Remaining disagreements (adjudicated by a third member): ______________________

Per `eval/judge_protocol.md` §1 the person who wrote an item may not be the only
grader of that item; this sheet was drafted with coding-agent assistance and the
questions have not been read by a second human yet, so every row above is pending.
