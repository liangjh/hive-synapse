# Agent Onboarding

An agent signs into a Hive workspace by knowing:

- workspace path
- actor id
- home node
- role
- current target/context pack

Minimum boot sequence:

```bash
hive validate <workspace>
hive context status <target> --workspace <workspace>
hive context compile <target> --workspace <workspace>
```

Agents may write personal/candidate/import/job/proposal records according to role policy. Shared publication requires proposal review and authorized apply.
