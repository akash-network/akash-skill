# Console API: Teams and Projects

Every Console user has a **personal account** and can belong to any number of **teams**. The API calls both *organizations* (`type` is `personal` or `team`). Each one has its own managed wallet and credits, and files its deployments into **projects**. Every organization, personal accounts included, has a **default project**.

An API key is created in one organization and acts only there, with its creator's role, optionally limited to one project. It never reaches its creator's other teams or personal account. A user who belongs to no team sees no change: requests run in the personal account and deployments land in its default project.

## Roles

Team roles, as `role` in `GET /v1/organizations`:

| Role | Deploys and changes deployments | Reads deployments | Changes team billing | Members, projects, budgets |
|---|---|---|---|---|
| `owner` | Every project | Every project | Yes | Everything, including deleting the team |
| `admin` | Every project | Every project | No | Everything except owners |
| `member` | Its projects | Its projects | No | Only projects where it is a project admin |
| `billing` | No | No | Yes | No |
| `viewer` | No | Its projects | No | No |

A member or viewer reaches **all projects** or **selected ones**. On a selected project its project role decides: `viewer` reads it, `member` also deploys into it and changes its deployments, `admin` also renames it and manages who else reaches it. A team `viewer` only reads, whatever its project role. In a personal account the user is the owner.

## Which team and project a request runs in

| Credential | Team | Projects |
|---|---|---|
| API key | The team the key was created in, always. A key from before teams (`organizationId: null`) acts in its creator's personal account. | A key bound to a project reaches only that one. Otherwise, every project its creator reaches. |
| Console session (`Authorization: Bearer`, the web app) | `x-organization-id`, else the team used last, else the personal account | Every project the user reaches |

The key follows its creator: if the creator's role changes, so do the key's rights, and once the creator leaves or is removed from the team, the key answers 403 `organization_forbidden`.

Two optional headers narrow a request:

| Header | Value | With an API key | Refused with |
|---|---|---|---|
| `x-organization-id` | Team id or slug | Can only repeat the key's own team; a key never switches teams | 400 `organization_mismatch` for another team than the key's; 403 `organization_forbidden` for a session that isn't a member |
| `x-project-id` | Project id (a UUID) | Limits the request to one project the key reaches | 403 `project_forbidden` |

Scripts with an API key need neither header. To act in another team, use a key created in that team.

### Find where a key acts

```bash
API=https://console-api.akash.network
curl -s "$API/v1/organizations" -H "x-api-key: $AKASH_API_KEY" | jq '.data[] | {id, name, slug, type, role}'
curl -s "$API/v1/projects" -H "x-api-key: $AKASH_API_KEY" | jq '.data[] | {id, name, isDefault, canDeploy: .access.canDeploy}'
```

With an API key, `GET /v1/organizations` lists only the key's team. `GET /v1/projects` lists the projects the request reaches, most recently active first; a key bound to a project sees only its own. `access.canDeploy` says whether the caller may deploy into that project and change its deployments.

## API keys bound to a team or a project

In Console, switch to the team, then open **Settings → API Keys**; the dialog offers **All projects** or one project. Over the API, `POST /v1/api-keys` creates the key in the team the request runs in, and `data.projectId` binds it to one project the caller reaches (404 otherwise):

```bash
curl -sX POST "$API/v1/api-keys" \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"data": {"name": "ci-checkout", "projectId": "<project id>"}}'
```

Every key in `GET /v1/api-keys` shows where it acts:

| Field | Meaning |
|---|---|
| `organizationId` | The team the key acts in. `null` for a key created before teams, which acts in its creator's personal account. |
| `projectId` | The only project the key reaches, or `null` when it reaches every project its creator does |

`GET /v1/api-keys` lists the caller's own keys in the current team only. A binding never changes (`PATCH` only renames), so to move a key, create a new one and delete the old one.

A key bound to a project:

- deploys into its project without being told (below), and reads and changes only that project's deployments
- reads its team and its project, but can't manage API keys, members, invitations, projects or billing settings (403), nor rename the team
- mints provider JWTs only for deployments it names (see [Provider tokens](#provider-tokens))

To give someone access to one project only, invite them to the team as a `member` with that project selected, and let them create their own key. A key you create acts with your role, so anyone holding it acts as you.

## Deploy into a project

`POST /v1/deployments` takes `data.projectId`. Without it, Console files the deployment:

1. in the only project the request may deploy into, when there is exactly one: a key bound to a project, an `x-project-id` header, or a member who may deploy into a single project;
2. otherwise in the team's default project.

When the caller may not deploy into that project, the create answers **400 `project_required`**: pass `data.projectId`, taken from `GET /v1/projects` where `access.canDeploy` is true. A `projectId` the caller can't deploy into, or that doesn't exist, answers 404.

```bash
PROJECT_ID=$(curl -s "$API/v1/projects" -H "x-api-key: $AKASH_API_KEY" \
  | jq -r '.data[] | select(.name == "prod" and .access.canDeploy) | .id')

curl -sX POST "$API/v1/deployments" \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -nc --rawfile sdl deploy.yaml --arg project "$PROJECT_ID" '{data: {sdl: $sdl, projectId: $project}}')"
```

Bids, `POST /v1/leases`, `PATCH`, the provider JWT and the close work on the dseq as usual; the deployment stays in its project until someone moves it.

## List by project, move, locate

```
GET   /v1/deployments?projectId=<id>
PATCH /v1/deployments/{dseq}/project
GET   /v1/deployment-locations/{dseq}
```

- **List.** `projectId` keeps the deployments filed in one project, and each listed deployment carries its `projectId`. A project the caller can't reach lists nothing, like one that doesn't exist. Without the filter the list spans every project the caller reaches; a team with more open deployments than one list can check answers 422, so filter by project.
- **Move.** `PATCH /v1/deployments/{dseq}/project` with `{ "data": { "projectId": "<target>" } }` refiles a deployment in another project of the same team and answers `{ "data": { "dseq", "projectId" } }`. Owners and admins only (403 otherwise; 404 when the deployment or the project is out of reach). Nothing changes on chain: the lease, the provider and the escrow stay; the deployment's alerts follow it. A deployment never moves between teams.
- **Locate.** `GET /v1/deployment-locations/{dseq}` answers `{ "data": { "organizationId", "organizationSlug", "projectId" } }`. With an API key it only looks within the key's reach, and answers 404 outside it.

## Project budgets

Owners and admins can give a project a monthly budget in USD (calendar months, UTC) with `POST /v1/project-budgets` (`projectId`, `monthlyAmountUsd`, `alertThresholdPercent`, `stopTopUps`). A create whose first deposit would take the project past it answers **403 `project_budget_exceeded`**, and `data.projectIds` names the project. With `stopTopUps`, the automatic top-ups of the project's running deployments stop at the budget too, so they run on their escrow until it is spent. Retrying doesn't help: an owner or admin raises the budget (`PATCH /v1/project-budgets/{id}`), or the next month starts. `GET /v1/project-budgets` shows `currentPeriod.committedUsd`.

## Team billing

A team pays from its own wallet, separate from every member's personal account: its own on-chain address, credits, cards and Auto recharge.

- Teams never get a free trial. A new team has no credits until an owner or billing member adds them.
- `GET /v1/balances` with a team's key reads the team's balance, in the same `balance`, `deployments` and `total` fields (**@account-and-funding.md**). Every member can read it.
- A team deployment's `deployment.id.owner` is the team wallet's address, not a member's.
- Credits, cards and Auto recharge are set on the team's **Billing** page in Console, by an owner or a billing member. There is no supported API for them, and nothing moves credits between a personal account and a team.
- A 402 (`insufficient_balance`, `balance_top_up_pending`) on a team key is about the team's credits. Ask an owner or billing member to add credits. `hasPaymentMethod` in `GET /v1/organizations` says whether the team has a card saved.

## Provider tokens

`POST /v1/create-jwt-token` mints tokens for the wallet of the request's team. Two rules apply on top of **@operations.md**:

- In a team, and for any request limited to some projects, `ttl` is at most 3600 seconds; more answers 400.
- A request is **limited to some projects** when its key is bound to a project, it sends `x-project-id`, or the key's creator is a team `member` or `viewer` (only owners and admins reach every project). Such a request must name each deployment: `access: "granular"` at the top and on every provider entry, each with its `deployments`. `full` and `scoped` answer 403 `project_forbidden`. Granting more than `status`, `events` and `logs` also needs the right to change those deployments.

```json
{
  "data": {
    "ttl": 1800,
    "leases": {
      "access": "granular",
      "permissions": [
        {
          "provider": "akash1prov...",
          "access": "granular",
          "deployments": [{ "dseq": 1785245500842, "gseq": 1, "oseq": 1, "services": ["web"], "scope": ["logs", "events", "status"] }]
        }
      ]
    }
  }
}
```

## Only from a signed-in session

Creating a team, accepting an invitation, leaving a team, deleting a team and deleting the account need a signed-in Console session. With an API key they answer **403 `session_required`**: do them in the Console web app.

## Errors

| Status | `code` | Meaning | Do this |
|---|---|---|---|
| 400 | `organization_mismatch` | `x-organization-id` names another team than the API key's | Drop the header, or use a key created in that team |
| 403 | `organization_forbidden` | The caller isn't a member of the team: the header names a team the user doesn't belong to, or the key's creator left or was removed | Use a key of a current member |
| 403 | `project_forbidden` | The request reaches outside its projects: `x-project-id` names a project the caller can't reach (or another project than the key's), a write targets a deployment filed in a project the caller can't change, or a provider JWT doesn't name its deployments one by one | Stay within the key's projects, name the deployments in the JWT, or use a key that reaches the other project |
| 400 | `project_required` | A create found no project to file the deployment in | Pass `data.projectId` |
| 403 | `project_budget_exceeded` | The deposit would take the project past its monthly budget; `data.projectIds` names it | An owner or admin raises the budget. Don't retry. |
| 403 | `project_limit_reached` | `POST /v1/projects` found the team at its project limit, given in `data.limit`: 10, counting the default project | Use an existing project, or have an owner or admin delete one it no longer uses (one with no open deployment) |
| 403 | `organization_limit_reached` | Creating a team found the user at their limit of teams they created that still exist, given in `data.limit`: 3 | Delete a team you created and no longer use, or join an existing team by invitation |
| 403 | `session_required` | A session-only action was sent with an API key | Do it in the Console web app |

A read of a deployment outside the caller's projects answers 404, as for one that doesn't exist. A `viewer` or `billing` member's key gets a plain 403 (`forbidden`) on a create, lease, patch or close.

## Team endpoints

All of these run in the request's team and take the same `x-api-key`; the live spec has their bodies.

| Task | Endpoint |
|---|---|
| The team, rename it (owner, admin) | `GET /v1/organizations`, `PATCH /v1/organizations/{id}` |
| Projects (only owners and admins create one; up to 10 per team, counting the default) | `GET`, `POST /v1/projects`; `GET`, `PATCH`, `DELETE /v1/projects/{id}` (delete only with no open deployment; the default project can't be deleted) |
| Who reaches a project | `GET /v1/projects/{id}/members`; `POST /v1/project-members`; `PATCH`, `DELETE /v1/project-members/{id}` |
| Members | `GET /v1/organization-members`; `PATCH`, `DELETE /v1/organization-members/{id}` |
| Invitations by email (accepting is session-only) | `GET`, `POST /v1/organization-invitations`; `DELETE /v1/organization-invitations/{id}` |
| Budgets | `GET`, `POST /v1/project-budgets`; `PATCH`, `DELETE /v1/project-budgets/{id}` |
| Spend per project, per deployment | `GET /v1/project-spend`, `GET /v1/deployment-spend` |
| What happened in the team | `GET /v1/organization-activities` |

## Related files

- **@authentication.md**: API keys
- **@deployment-endpoints.md**: create, list, move and close deployments
- **@account-and-funding.md**: balance and automatic funding
- **@operations.md**: provider JWTs, logs and shell
