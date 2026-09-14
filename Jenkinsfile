pipeline {
    agent { label 'docker-cleanup' }
    options {
        disableConcurrentBuilds()
        skipDefaultCheckout(true)
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '10'))
    }
    parameters {
        booleanParam(name: 'DRY_RUN', defaultValue: true, description: 'Preview candidates without deleting images')
        string(name: 'MIN_AGE_HOURS', defaultValue: '168', description: 'Image creation age: 24–87600 hours')
        string(name: 'CLEANUP_LABEL', defaultValue: 'cleanup.enabled=true', description: 'Required image label, key=value')
    }
    stages {
        stage('Checkout') {
            steps {
                deleteDir()
                checkout scm
            }
        }
        stage('Test and Validate') {
            steps {
                sh 'python3 -m unittest discover -s tests -v'
                sh 'docker version'
            }
        }
        stage('Preview Cleanup') {
            steps {
                withEnv(["CLEANUP_LABEL=${params.CLEANUP_LABEL}", "MIN_AGE_HOURS=${params.MIN_AGE_HOURS}"]) {
                    sh 'python3 scripts/cleanup_images.py plan --label "$CLEANUP_LABEL" --hours "$MIN_AGE_HOURS"'
                }
                archiveArtifacts artifacts: 'cleanup-plan.json', fingerprint: true
                script {
                    env.HAS_CANDIDATES = sh(script: 'python3 -c \'import json; print(bool(json.load(open("cleanup-plan.json"))["images"]))\'', returnStdout: true).trim()
                    currentBuild.description = params.DRY_RUN ? 'Preview only' : 'Deletion requested'
                }
            }
        }
        stage('Approve Deletion') {
            when { expression { !params.DRY_RUN && env.HAS_CANDIDATES == 'True' } }
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    input message: 'Review cleanup-plan.json. Delete these eligible local Docker images?', ok: 'Delete reviewed images'
                }
            }
        }
        stage('Delete Reviewed Images') {
            when { expression { !params.DRY_RUN && env.HAS_CANDIDATES == 'True' } }
            steps {
                withEnv(["CLEANUP_LABEL=${params.CLEANUP_LABEL}", "MIN_AGE_HOURS=${params.MIN_AGE_HOURS}"]) {
                    sh 'python3 scripts/cleanup_images.py apply --label "$CLEANUP_LABEL" --hours "$MIN_AGE_HOURS"'
                }
            }
        }
    }
    post {
        always {
            archiveArtifacts artifacts: 'cleanup-results.json', allowEmptyArchive: true
        }
        success { echo 'Cleanup completed. Review the archived plan and results.' }
        failure { echo 'Cleanup failed. Review the console and any partial results before retrying.' }
        aborted { echo 'Cleanup aborted; inspect results if deletion had already started.' }
    }
}
