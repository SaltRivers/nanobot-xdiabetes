# Security Policy

## Reporting a Vulnerability

If you discover a security issue in X-Diabetes:

1. **Do not** open a public issue first.
2. Contact the repository maintainers privately.
3. Include:
   - a clear description
   - reproduction steps
   - impact
   - a suggested fix if available

We aim to respond quickly and coordinate a responsible fix path.

## Security Best Practices

### 1. API Keys

```bash
chmod 600 ~/.x-diabetes/config.json
```

Recommendations:

- Store API keys in `~/.x-diabetes/config.json` with `0600` permissions.
- Use separate keys for development and production.
- Rotate credentials regularly.
- Prefer dedicated secrets management in production deployments.

### 2. Channel Access Control

Always configure `allowFrom` for production-facing channels.

### 3. Command Execution

The runtime can execute shell commands through tools, so:

- review tool usage carefully
- avoid running as root
- use a dedicated service account
- do not disable security checks

### 4. Filesystem Protection

- protect `~/.x-diabetes`
- audit logs regularly
- avoid granting unrestricted access to sensitive paths

### 5. Network Safety

- use HTTPS for external APIs whenever possible
- restrict outbound access if needed
- keep bridge authentication material in `~/.x-diabetes/whatsapp-auth` protected

### 6. Dependency Updates

```bash
pip install pip-audit
pip-audit
pip install --upgrade x-diabetes-ai
```

For the Node.js bridge:

```bash
cd bridge
npm audit
npm audit fix
```

### 7. Production Deployment Checklist

- [ ] API keys stored securely
- [ ] Config file permissions set to `0600`
- [ ] `allowFrom` lists configured
- [ ] Running as a non-root user
- [ ] Dependencies updated
- [ ] Logs monitored
- [ ] Rate limits configured on providers
- [ ] Custom skills/tools reviewed

### 8. Incident Response

If you suspect compromise:

1. revoke exposed API keys
2. inspect logs for unauthorized access
3. rotate credentials
4. update dependencies
5. report the incident privately

## Known Limitations

Current limitations include:

- no built-in end-user rate limiting
- plain-text local config storage
- no automatic session expiry
- intentionally conservative command filtering rather than full sandboxing

## Data Privacy

- logs may contain sensitive information
- provider prompts leave the local machine
- chat and workflow history are stored locally under `~/.x-diabetes`

## License

See `LICENSE` for details.
