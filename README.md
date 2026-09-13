# Jenkins cleanup scaffold

A minimal Jenkins Declarative Pipeline for planning Docker image retention. It currently performs no image or registry deletion.

## Use

Create a Jenkins Pipeline job from this repository and set the script path to `Jenkinsfile`. A Jenkins installation with Declarative Pipeline support and an available agent is required. The two stages print reminders for configuration and a future dry run.

Before implementing cleanup, choose the registry, retention policy, credentials stored in Jenkins, and an auditable dry-run procedure. The duplicate `Jenkinsfile copy` has been removed so there is one entry point.

Validation: static review only; no Jenkins job was executed.
