pipeline {
    agent any

    stages {
        stage('Configure Docker Image Properties') {
            steps {
                // Set the Docker image retention properties using curl command
                sh 'curl -u admin:M1234567m -X PUT "http://localhost:8082/artifactory/api/storage/image1/myimage?properties=docker.retention.maxDays=1;docker.retention.maxCount=1"'
            }
        }
        stage('Cleanup Docker Images') {
            steps {
                // Execute the cleanDockerImages plugin with dryRun=true using curl command
                sh 'curl -u admin:M1234567m -X POST "http://localhost:8082/artifactory/api/plugins/execute/cleanDockerImages?params=dryRun=true"'
            }
        }
    }
}
