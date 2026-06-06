# Host Port Allocation — pragmata-001

Public ports **80/443** belong to shared Traefik. Do not use them.
Everything below is `127.0.0.1`-bound — access via SSH tunnel only.
**Add a row before assigning a new host port; never reuse a taken entry.**

```bash
# SSH tunnel examples:
ssh -L 9030:localhost:9030   root@pragmata-001    # InkBytes MinIO console
ssh -L 15683:localhost:15683 root@pragmata-001    # InkBytes RabbitMQ mgmt
```

| Project     | Service              | Container port | Host bind (127.0.0.1:host) | Notes                          |
|-------------|----------------------|----------------|----------------------------|--------------------------------|
| _traefik_   | http / https         | 80 / 443       | 0.0.0.0 (public)           | Shared — DO NOT USE            |
| archon      | postgres             | 5432           | 5443                       | +11 offset; internal tooling   |
| archon      | redis                | 6379           | 6390                       | +11 offset; internal tooling   |
| br-lexigo   | minio console        | 9001           | 9022                       | Admin via SSH tunnel           |
| **inkbytes**| **minio console**    | **9001**       | **9030**                   | `ssh -L 9030:localhost:9030`   |
| **inkbytes**| **rabbitmq mgmt**    | **15672**      | **15683**                  | `ssh -L 15683:localhost:15683` |

## Next available blocks

- MinIO console: `9040`, `9050`, …
- RabbitMQ mgmt: `15693`, `15703`, …
- Postgres (if ever needed on host): `5453`, `5463`, …

## Notes

- InkBytes Postgres, RabbitMQ, MinIO API, Ollama, Curator, Messor, Reader, and Backoffice-FPM
  are all **internal-only** — no host port binding.
- The two public surfaces (Reader `:3000`, Backoffice nginx `:80`) are routed exclusively
  through Traefik labels — projects never publish 80/443.
