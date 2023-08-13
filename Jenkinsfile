pipeline {
    agent any
    
    environment {
        REPO_NAME = "test-cleanup-docker"
        USERNAME = #
        PASSWORD = #
    }
    
    stages {
        stage('Cleanup Docker Images') {
            steps {
                script {
                    // Step 1: Get the list of image names
                    def response = sh(script: """\
                        curl -u ${env.USERNAME}:${env.PASSWORD} -X POST "https://jfrog.onebank.local/artifactory/api/search/aql" -H "Content-Type: text/plain" -d 'items.find({
                            "repo": "${env.REPO_NAME}",
                            "@docker.repoName": "*"
                        }).include("name", "@docker.repoName", "@docker.manifest", "stat.downloads")'
                    """, returnStdout: true).trim()
                    
                    if (currentBuild.resultIsBetterOrEqualTo("FAILURE")) {
                        error("Failed to retrieve image paths from Artifactory.")
                    }
                    
                    // Step 2: Extract image names and remove duplicates
                    def imageNames = sh(script: """\
                        echo '$response' | jq -r '.results[] | .properties[] | select(.key == "docker.repoName") | .value' | awk '!seen[\$0]++'
                    """, returnStdout: true).trim()
                    
                    echo "Image names: ${imageNames}"
                    
                    // Step 3: Loop through and set properties for each image
                    imageNames.split('\n').each { image ->
                        echo "Processing image: ${image}"
                        
                        sh(script: """\
                            curl -u ${env.USERNAME}:${env.PASSWORD} -X PUT "https://jfrog.onebank.local/artifactory/api/storage/${env.REPO_NAME}/${image}?properties=docker.retention.maxCount=1"
                        """)
                        
                        if (currentBuild.resultIsBetterOrEqualTo("FAILURE")) {
                            echo "Failed to set property for image: ${image}"
                        } else {
                            echo "Successfully set property for image: ${image}"
                        }
                    }
                }
            }
        }
        
        stage('Clean Docker Images Plugin') {
            steps {
                script {
                    sh(script: """\
                        curl -u ${env.USERNAME}:${env.PASSWORD} -X POST "https://jfrog.onebank.local/artifactory/api/plugins/execute/cleanDockerImages?params=dryRun=true"
                    """)
                }
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
    }
}
