# Torque response shapes

Truncated examples of what each endpoint returns. Use these to know which fields to parse and surface to the user. Only fields commonly needed are listed — full swagger has every field.

## GET /spaces

```json
[
  { "name": "team-platform", "description": "...", "owner": "user@example.com" }
]
```
Useful: `name`.

## GET /spaces/{space}/blueprints

```json
[
  {
    "id": "...",
    "name": "ec2-instance",
    "display_name": "EC2 Instance",
    "repository_name": "qtorque",
    "blueprint_folder": "blueprints/aws",
    "sub_type": "blueprint",
    "description": "...",
    "labels": [{ "key": "team", "value": "platform" }]
  }
]
```
Useful: `name`, `description`, `repository_name`, `sub_type`, `labels`.

## GET /spaces/{space}/blueprints/{name}/editable

```json
{ "content": "spec_version: 2\nkind: blueprint\n..." }
```
Useful: `content` (raw YAML string).

## POST /spaces/{space}/validations/blueprints

```json
{
  "is_valid": false,
  "errors": [
    { "message": "...", "line": 12, "column": 3, "path": "grains.app" }
  ],
  "warnings": []
}
```
Useful: `is_valid`, `errors[].message`, `errors[].line`.

## GET /spaces/{space}/catalog

```json
[
  {
    "id": "...",
    "name": "ec2-instance",
    "display_name": "EC2 Instance",
    "description": "...",
    "labels": [],
    "repository_name": "qtorque",
    "icon_url": "...",
    "is_favorite": false,
    "inputs": [
      { "name": "region", "type": "string", "required": true, "default": null }
    ]
  }
]
```
Useful: `name`, `description`, `inputs[]` (count required-without-default to surface "inputs required" column).

## GET /spaces/{space}/environments

```json
[
  {
    "id": "abc123",
    "name": "my-env",
    "blueprint_name": "ec2-instance",
    "computed_status": "Active",
    "owner": { "email": "user@example.com" },
    "start_time": "2026-05-15T10:00:00Z",
    "end_time": "2026-05-15T12:00:00Z",
    "labels": []
  }
]
```
Useful: `id`, `name`, `computed_status` (or `status`), `blueprint_name`.

## GET /spaces/{space}/environments/{env_id}

```json
{
  "id": "abc123",
  "name": "my-env",
  "blueprint_name": "...",
  "status": "Launching",
  "details": { "errors": [] },
  "grains": [
    {
      "name": "app",
      "kind": "helm",
      "status": "Active",
      "errors": [],
      "progress": 100,
      "depends_on": ["infra"]
    }
  ],
  "inputs": { "region": "us-east-1" },
  "outputs": { "url": "https://..." }
}
```
Useful for debug: `status` (top), `grains[].name`, `grains[].kind`, `grains[].status`, `grains[].errors[]`, `grains[].depends_on`, `details.errors`.

## GET /spaces/{space}/environments/{env_id}/workflows_v2

```json
{
  "workflows": [
    {
      "id": "...",
      "workflow_name": "...",
      "status": "Active",
      "start_time": "..."
    }
  ]
}
```
Useful: `workflows[].workflow_name`, `workflows[].status`.

## POST /spaces/{space}/environments (launch / run_workflow)

```json
{ "id": "env-abc123", "name": "my-env", "status": "Launching" }
```
Sometimes returns a bare string id (older API). Example scripts handle both.

## GET /settings/environmentfeed?sandbox_id={env_id}

```json
[
  {
    "timestamp": "2026-05-15T10:00:01Z",
    "type": "info" /* or "error" */,
    "message": "Provisioning agent...",
    "grain_name": "app"
  }
]
```
Useful when `grains[].errors[]` is empty but env failed — feed has richer messages.

## GET /resource (Inventory)

```json
{
  "resources": [
    {
      "id": "Ab12Cd34Ef56",
      "name": "blade-1-1",
      "identifier": "0123456789abcdef01234567",
      "type": "compute.Blade",
      "provider": "intersight-site-a",
      "provider_type": "intersight",
      "attributes": [{ "name": "Model", "value": "UCSX-210C-M6", "value_type": "String", "description": "" }],
      "reservation_status": "available",
      "reserver_details": null,
      "excluded_from_reserving": false,
      "excluded_from_reserving_reason": null
    }
  ],
  "paging_info": { "full_count": 9, "requested_page": 1, "total_pages": 1 }
}
```
Useful: `id` (the value a resource input takes), `name`, `identifier` (external id), `reservation_status` + `reserver_details {env_id, space_name}`, `excluded_from_reserving`, `attributes`. Some builds return a bare list. `paging_info.take` > 80 is 422 `MAX_PAGE_SIZE_EXCEEDED`.

## POST /spaces/{space}/catalog/inputs_allowed_values

```json
[
  {
    "name": "Node",
    "allowed_values": [
      {
        "value": "Gh78Ij90Kl12",
        "display_value": "ip-10-0-1-23.ec2.internal",
        "extra_details": { "identifier": "Node.ip-10-0-1-23.ec2.internal", "provider_name": "my-eks", "provider_type": "kubernetes", "attributes": {}, "details_type": "resource" }
      }
    ],
    "errors": [],
    "has_more": false
  }
]
```
Useful: `allowed_values[].value` (reference id), `allowed_values[].display_value`, and **`errors`** — selector problems come back here with HTTP 200 (`VALUE_CANT_BE_RESOLVED`, `EMPTY_PROPERTY`, `InternalServerError`), not as an HTTP error.
