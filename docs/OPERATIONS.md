# Operations: the hosted checker

How the hosted checker runs, what it costs, how to release, roll back or take it offline, and
what it keeps. For maintainers. Facts as of 25 Oct 2026; a change to any of them updates this
file in the same pull request.

## Who

- Provisional steward: DVM Consulting, Inc. (acting: Sean Delaney). DVM Consulting pays the
  costs below until a governance body decides how the project is hosted and funded
  ([disclosure of interest](https://github.com/openanimalnutrition/animal-nutrition-ig/blob/main/GOVERNANCE.md)).
- Privacy questions, misuse and security reports: openanimalnutrition@dvmconsulting.com, an
  alias that reaches the steward. Errors in a rule or a value: GitHub issues (public).
- Second maintainer: none yet.

## What runs where

| What | Where |
|---|---|
| AWS account | 950607791713, "Open Animal Nutrition Production", in DVM Consulting's AWS organization. Root email admin+awsoan@dvmconsulting.com, with MFA. Day-to-day: the AWS access portal, the management account, then switch role `OrganizationAccountAccessRole` into 950607791713 ("OAN Prod"). |
| Service | Amazon Lightsail container service `oan-checker`, us-east-1, power Nano (0.25 vCPU, 512 MB), scale 1. |
| Image | `ghcr.io/openanimalnutrition/animal-nutrition-checker` (public), built by `.github/workflows/image.yml` on every push to main after the contract tests pass. The deployment pins it by digest. |
| Deployment | Container `checker`; port 8790, HTTP; public endpoint `checker:8790`; health check path `/`, success codes 200-499 (the health check arrives with an internal Host, which the Host check answers with 400). Environment below. |
| Names | openanimalnutrition.org, www.openanimalnutrition.org and checker.openanimalnutrition.org serve the GUI; the MCP address to publish is https://checker.openanimalnutrition.org/mcp. The service's own address, oan-checker.c5kapc540385r.us-east-1.cs.amazonlightsail.com, also works. |
| Certificate | Lightsail certificate `oan-checker-domains` for the three names, attached to the service. It renews automatically while its validation CNAMEs stay in DNS. |
| DNS | Route 53 hosted zone Z01009783JJPPE1GBH7KU, in the same account: the 3 certificate-validation CNAMEs, 3 A alias records to the Lightsail us-east-1 container zone Z06246771KYU0IRHI74W4, and GitHub's organization-verification TXT. Alias records to Lightsail can be made only with the AWS CLI (CloudShell), not in the Route 53 console. Query logging must stay off (see "What the hosted checker keeps"). |
| Domain registration | Namecheap, paid to 29 Jun 2027, auto-renew on, in the steward's Namecheap account. Its nameservers delegate to the Route 53 zone. |

Environment (keep unchanged across deployments):

```
OAN_HOSTS=oan-checker.c5kapc540385r.us-east-1.cs.amazonlightsail.com,openanimalnutrition.org,www.openanimalnutrition.org,checker.openanimalnutrition.org
OAN_ORIGINS=https://oan-checker.c5kapc540385r.us-east-1.cs.amazonlightsail.com,https://openanimalnutrition.org,https://www.openanimalnutrition.org,https://checker.openanimalnutrition.org
```

## Costs

| Item | Cost |
|---|---|
| Lightsail container service, Nano x 1 | $7 a month, including 500 GB of data out; above that, from $0.09 per GB. Charged while disabled; only deleting the service stops the charge. |
| Route 53 hosted zone | $0.50 a month, plus DNS queries |
| Domain | Namecheap's yearly .org renewal |
| Certificate, GitHub organization, public image | no charge |

AWS Budgets "OAN monthly cost": $15 a month, emails admin+awsoan@dvmconsulting.com.

## Release a new version

A merge to main publishes an image; the live site changes only when a new deployment is made.

1. Wait for the merge commit's checks, including the image workflow, to pass.
2. Get the image's digest (no login needed):

   ```
   SHA=<full merge commit sha>
   R=openanimalnutrition/animal-nutrition-checker
   TOKEN=$(curl -s "https://ghcr.io/token?scope=repository:$R:pull" | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
   curl -sI -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.oci.image.index.v1+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json" "https://ghcr.io/v2/$R/manifests/sha-$SHA" | grep -i docker-content-digest
   ```

3. Lightsail console > Containers > `oan-checker` > Deployments > Modify your deployment. Set
   the image to `ghcr.io/openanimalnutrition/animal-nutrition-checker@<digest>`, where
   `<digest>` is the whole `sha256:...` value from step 2; leave everything else unchanged,
   and save and deploy. A failed deployment leaves the previous one
   running.
4. Check:

   ```
   curl -sI https://checker.openanimalnutrition.org/    # 200, strict-transport-security, no "server: uvicorn"
   curl -s https://checker.openanimalnutrition.org/ | grep -o 'Code [0-9.]*, data [^ ]*'
   curl -s -X POST https://checker.openanimalnutrition.org/mcp -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"check","version":"1"}}}' | grep -o '"serverInfo":{[^}]*}'
   ```

## Roll back

Repeat "Release a new version", steps 2 to 4, with the merge commit of the release to return
to. Its image is pinned by digest, so that release comes back exactly. Lightsail also keeps
the last 50 deployment versions.

## Take the site offline (emergency)

When: misuse that costs money (data out above 500 GB a month) or harms others, a security
flaw, or a wrong result that could harm animals before a fix can be deployed.

Disabling makes every name answer 503 and keeps the deployment, its images and settings;
re-enabling restores the last deployment unchanged. Logs and metrics still expire as usual.
In AWS CloudShell, in the "OAN Prod" role:

```
aws lightsail update-container-service --region us-east-1 --service-name oan-checker --is-disabled
aws lightsail get-container-services --region us-east-1 --service-name oan-checker --query 'containerServices[0].[state,isDisabled]'
for h in openanimalnutrition.org www.openanimalnutrition.org checker.openanimalnutrition.org; do curl -s -o /dev/null -w "$h %{http_code}\n" https://$h/; done
```

Repeat the last two commands until the state is `DISABLED` and every name answers 503.

Back online: the first command with `--no-is-disabled`.

The service is still charged while disabled. Deleting it (`aws lightsail
delete-container-service`) stops the charge but loses the deployment history and the
service's own address; bringing it back means a new service, deployment, certificate and
alias records. Delete only to shut the service down for good.

Afterwards, record what happened and why in a public GitHub issue, once any security flaw is
fixed.

## Misuse and security reports

- Reports arrive at the contact address above.
- What can be seen: Lightsail > Containers > `oan-checker` > Metrics (CPU and memory) and
  Deployments > Open log (3 days; start-up lines and errors only), and the AWS bill (data
  out). There is no request
  log, so a client cannot be identified or blocked by address in the service itself.
- No per-address limits, by design: AI clients call from their providers' shared addresses,
  so such a limit would block every user of a client at once. Fixed limits: request bodies of
  at most 32 KB, 16 concurrent requests, a 5 s keep-alive, one Nano node with no
  autoscaling.
- If misuse continues: take the site offline (above), or put a CDN with a firewall in front
  (not set up; on AWS, CloudFront with AWS WAF).

## What the hosted checker keeps

The About page (`server/pages/about.html`, served at `/about`) is the public statement. It
rests on these facts; a change to any of them updates the About page in the same pull
request:

- uvicorn runs with `--no-access-log` (the Dockerfile's `CMD`), and the app has no logging of
  its own. The contract test `Log.test_no_request_content_or_address_in_the_log` sends
  requests with a marker in every field, header, path and tool argument, and fails if the
  marker or a client address appears in the server's output (`tests/contract/`).
- What remains in the output: uvicorn's start-up and shutdown lines, a fixed "Invalid HTTP
  request received." for a malformed request, and, if the server fails unexpectedly, the
  error's traceback, which can include part of the request.
- Lightsail keeps the container log for 3 days and CPU and memory metrics for up to 15
  months, and offers no request log.
- The pages set no cookies and run no scripts, and the content security policy loads nothing
  from other sites.
- Route 53 query logging stays off. Check in CloudShell: `aws route53
  list-query-logging-configs --hosted-zone-id Z01009783JJPPE1GBH7KU` must list none.

## Not yet set up

- A second maintainer, outside DVM Consulting, with a limited role in the AWS account and the
  GitHub organization.
- A monthly pull request that updates the base image digest and the package lock (the image
  is rebuilt only on a push to main, and both are pinned).
- An uptime check.

## Handover

To the governance body, when it decides to take these on:

- AWS account: AWS Organizations can move a member account directly to another organization
  (announced 19 Nov 2025). Change the root email to the new holder's.
- GitHub organization: add the new owners, then remove DVM Consulting's.
- Domain: transfer the Namecheap registration, or move it into the AWS account.
- Contact: replace openanimalnutrition@dvmconsulting.com in `server/pages/about.html` and in
  this file.

Everything is CC0, so anyone can also run their own copy from the public image.
