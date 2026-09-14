# Jenkins Docker image cleanup

A configurable Jenkins pipeline for previewing and removing old, explicitly labelled, unused dangling images from a dedicated Docker daemon. Runs default to **dry run**. Remote registries, containers, volumes and build caches are outside its scope.

## Setup

1. Configure a trusted Linux Jenkins agent with label `docker-cleanup`, Python 3.9+, Git, and a Docker CLI connected to the intended daemon.
2. Create a **Pipeline from SCM** job using this repository and `Jenkinsfile`. Jenkins needs Declarative Pipeline, Git, Pipeline Input Step and the standard Pipeline artifact steps.
3. Build disposable images with `docker build --label cleanup.enabled=true ...`. Images without the configured label are retained.
4. Run with the default parameters and review the archived `cleanup-plan.json`.
5. To delete candidates, start a new build with `DRY_RUN=false`, review that build's plan, and approve the Jenkins input prompt within five minutes.

The job checks out a clean workspace, runs offline unit tests, verifies Docker connectivity, generates a plan and archives it before requesting approval. Empty plans skip approval and deletion. Total execution timeout is 30 minutes after agent allocation; Jenkins retains 20 builds and artifacts from 10 builds.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `DRY_RUN` | `true` | Plan only; no image removal |
| `MIN_AGE_HOURS` | `168` | Minimum time since image creation, from 24 to 87600 hours |
| `CLEANUP_LABEL` | `cleanup.enabled=true` | Exact required image label; key and value allow letters, digits, dots, underscores and hyphens |

## Retention and deletion

Candidates must have no tags, be older than the age threshold, have the exact label and be unused by both running and stopped containers. Age means creation time, not last use. Tagged releases are always retained; the pipeline does not implement keep-last-N for tagged images.

Apply validates the daemon identity and policy against the saved plan, then rechecks eligibility before each removal. It only removes IDs present in the reviewed plan using `docker image rm --no-prune` without force. Newly discovered images are not added. Images no longer eligible are skipped. A Docker error fails the build and archives partial results; already deleted images cannot be rolled back. Reported sizes may share layers and are not estimates of reclaimed disk space.

Use a dedicated daemon without competing build/tag/pull/cleanup activity during execution. Rechecking and removal are separate Docker operations, so they cannot eliminate every race with another client. `disableConcurrentBuilds()` only serializes this Jenkins job, not other jobs or Docker clients. Docker access is privileged: restrict who can edit the pipeline, start deletion runs and approve them through Jenkins permissions. The input step uses Jenkins' configured approval permissions; this repository does not define an approver group.

## Local verification

```sh
python3 -m unittest discover -s tests -v
python3 scripts/cleanup_images.py plan --label cleanup.enabled=true --hours 168
```

The tests use fake Docker responses and never delete real images. The plan command requires Docker and is read-only. Jenkins execution and integration with a real Docker daemon must be validated in your environment before enabling deletion.

References: [Jenkins Declarative Pipeline](https://www.jenkins.io/doc/book/pipeline/syntax/) and [Docker image removal](https://docs.docker.com/reference/cli/docker/image/rm/).
