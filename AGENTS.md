# RetroArch on OpenShift

One personal session on worker-0. Keep the workload non-root and keep GPU plugin
permissions separate. Do not disable host SELinux or grant the application the
privileged SCC. Library/state PVCs must survive uninstall. Never commit login
secrets, ROMs, BIOS files, or recovery archives. Read README.md before deploying.

Run scripts/check.sh for local validation. Deployment and hardware results belong
in docs/validation.md; distinguish checks actually performed from manual tests.
