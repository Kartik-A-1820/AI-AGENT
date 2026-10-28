# Security and data boundaries

AI-AGENT is a local assistant prototype, not a public multi-user service.

- Generated Python is disabled by default. Opt-in execution requires a prebuilt local Docker image; there is no host-Python fallback.
- The runner restricts network, mounts, privileges, resources, time, and output. Containers share the host kernel. A Docker daemon/image smoke test is required on the deployment machine.
- File tools perform resolved-path checks. They are not a protection boundary against concurrent hostile host processes.
- Connected-service tools run in the host process. Prompt instructions ask for action confirmation; tool calls do not have an independent approval gate.
- Local memory and OAuth tokens contain private data. External inference and tools can transmit content to their providers.

Keep the service bound to a trusted local environment. Do not add host directories, credentials, or a Docker socket to the code-runner image or job mount.

Do not post credentials or private data in a public issue. For a vulnerability, contact the maintainer privately at [anagawadi.kartik@gmail.com](mailto:anagawadi.kartik@gmail.com) with a minimal redacted reproduction. Do not include working tokens. Rotate any credential exposed in a report or commit.
