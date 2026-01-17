# Example: IP Endpoint Lease

SDL configurations using dedicated IP addresses for deployments.

## Use Case

- Custom domain mapping with DNS A records
- Non-HTTP services (SSH, gaming, mail)
- Services requiring fixed IP addresses
- Multi-port applications

## Version Requirement

IP endpoints require SDL version 2.1:

```yaml
version: "2.1"
```

## Basic IP Lease

```yaml
version: "2.1"

services:
  web:
    image: nginx:latest
    expose:
      - port: 80
        as: 80
        to:
          - ip: public-ip
      - port: 443
        as: 443
        to:
          - ip: public-ip

endpoints:
  public-ip:
    kind: ip

profiles:
  compute:
    web:
      resources:
        cpu:
          units: 1
        memory:
          size: 1Gi
        storage:
          size: 5Gi

  placement:
    dcloud:
      pricing:
        web:
          denom: uakt
          amount: 1000

deployment:
  web:
    dcloud:
      profile: web
      count: 1
```

## Game Server Example

```yaml
version: "2.1"

services:
  gameserver:
    image: itzg/minecraft-server:latest
    env:
      - "EULA=TRUE"
      - "TYPE=PAPER"
      - "MEMORY=4G"
    expose:
      - port: 25565
        as: 25565
        proto: tcp
        to:
          - ip: game-ip
      - port: 25565
        as: 25565
        proto: udp
        to:
          - ip: game-ip
    params:
      storage:
        world-data:
          mount: /data

endpoints:
  game-ip:
    kind: ip

profiles:
  compute:
    gameserver:
      resources:
        cpu:
          units: 4
        memory:
          size: 6Gi
        storage:
          - name: default
            size: 1Gi
          - name: world-data
            size: 20Gi
            attributes:
              persistent: true
              class: beta2

  placement:
    dcloud:
      pricing:
        gameserver:
          denom: uakt
          amount: 5000

deployment:
  gameserver:
    dcloud:
      profile: gameserver
      count: 1
```

## SSH Access Example

```yaml
version: "2.1"

services:
  dev:
    image: lscr.io/linuxserver/openssh-server:latest
    env:
      - "PUID=1000"
      - "PGID=1000"
      - "TZ=UTC"
      - "PUBLIC_KEY=ssh-rsa AAAA..."
      - "SUDO_ACCESS=true"
    expose:
      - port: 2222
        as: 22
        proto: tcp
        to:
          - ip: dev-ip

endpoints:
  dev-ip:
    kind: ip

profiles:
  compute:
    dev:
      resources:
        cpu:
          units: 2
        memory:
          size: 4Gi
        storage:
          - name: default
            size: 1Gi
          - name: home
            size: 50Gi
            attributes:
              persistent: true
              class: beta2

  placement:
    dcloud:
      pricing:
        dev:
          denom: uakt
          amount: 3000

deployment:
  dev:
    dcloud:
      profile: dev
      count: 1
```

## Multi-Service with Separate IPs

```yaml
version: "2.1"

services:
  frontend:
    image: nginx:latest
    expose:
      - port: 80
        as: 80
        to:
          - ip: frontend-ip
      - port: 443
        as: 443
        to:
          - ip: frontend-ip

  api:
    image: myapi:latest
    expose:
      - port: 8080
        as: 80
        to:
          - ip: api-ip
      - port: 8443
        as: 443
        to:
          - ip: api-ip

endpoints:
  frontend-ip:
    kind: ip
  api-ip:
    kind: ip

profiles:
  compute:
    frontend:
      resources:
        cpu:
          units: 0.5
        memory:
          size: 512Mi
        storage:
          size: 1Gi

    api:
      resources:
        cpu:
          units: 2
        memory:
          size: 2Gi
        storage:
          size: 10Gi

  placement:
    dcloud:
      pricing:
        frontend:
          denom: uakt
          amount: 500
        api:
          denom: uakt
          amount: 2000

deployment:
  frontend:
    dcloud:
      profile: frontend
      count: 1
  api:
    dcloud:
      profile: api
      count: 1
```

## Mail Server Example

```yaml
version: "2.1"

services:
  mail:
    image: mailserver/docker-mailserver:latest
    env:
      - "OVERRIDE_HOSTNAME=mail.example.com"
      - "ENABLE_SPAMASSASSIN=1"
      - "ENABLE_CLAMAV=1"
    expose:
      - port: 25
        as: 25
        proto: tcp
        to:
          - ip: mail-ip
      - port: 587
        as: 587
        proto: tcp
        to:
          - ip: mail-ip
      - port: 993
        as: 993
        proto: tcp
        to:
          - ip: mail-ip
    params:
      storage:
        mail-data:
          mount: /var/mail
        mail-state:
          mount: /var/mail-state

endpoints:
  mail-ip:
    kind: ip

profiles:
  compute:
    mail:
      resources:
        cpu:
          units: 2
        memory:
          size: 4Gi
        storage:
          - name: default
            size: 1Gi
          - name: mail-data
            size: 50Gi
            attributes:
              persistent: true
              class: beta2
          - name: mail-state
            size: 10Gi
            attributes:
              persistent: true
              class: beta2

  placement:
    dcloud:
      pricing:
        mail:
          denom: uakt
          amount: 4000

deployment:
  mail:
    dcloud:
      profile: mail
      count: 1
```

## Hybrid: Global + IP Endpoint

```yaml
version: "2.1"

services:
  web:
    image: nginx:latest
    expose:
      # Default Akash hostname (HTTPS with auto-cert)
      - port: 80
        as: 80
        to:
          - global: true
      # Dedicated IP for custom domain
      - port: 80
        as: 8080
        to:
          - ip: custom-ip
      - port: 443
        as: 8443
        to:
          - ip: custom-ip

endpoints:
  custom-ip:
    kind: ip

profiles:
  compute:
    web:
      resources:
        cpu:
          units: 1
        memory:
          size: 1Gi
        storage:
          size: 5Gi

  placement:
    dcloud:
      pricing:
        web:
          denom: uakt
          amount: 1500

deployment:
  web:
    dcloud:
      profile: web
      count: 1
```

## DNS Configuration

After deployment, configure your DNS:

1. Get the leased IP from deployment status
2. Create DNS A record:
   ```
   example.com.    A    <leased-ip>
   www.example.com.    A    <leased-ip>
   ```
3. For mail servers, add MX and SPF records:
   ```
   example.com.    MX    10 mail.example.com.
   mail.example.com.    A    <leased-ip>
   example.com.    TXT    "v=spf1 ip4:<leased-ip> -all"
   ```

## Best Practices

1. **Use v2.1**: IP endpoints require version "2.1"
2. **Declare before use**: Define endpoints before referencing them
3. **Use all declared endpoints**: Unused endpoints cause validation errors
4. **Consider costs**: IP leases have additional fees beyond compute
5. **Protocol awareness**: Specify `proto: udp` for UDP services
6. **Multiple ports**: Same IP can expose multiple ports
