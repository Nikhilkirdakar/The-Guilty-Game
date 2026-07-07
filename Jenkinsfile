pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 1, unit: 'HOURS')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    environment {
        PYTHON = 'python'
        VENV_DIR = '.venv'
        TGG_HEADLESS = 'true'
        TGG_BROWSER = 'chrome'
    }

    stages {
        stage('Checkout') {
            steps {
                echo '====== Cloning from GitHub ======'
                checkout scm
                sh 'git log --oneline -5'
            }
        }

        stage('Setup') {
            steps {
                echo '====== Creating Virtual Environment ======'
                script {
                    if (isUnix()) {
                        sh '''
                            ${PYTHON} -m venv ${VENV_DIR}
                            . ${VENV_DIR}/bin/activate
                            ${PYTHON} -m pip install --upgrade pip
                            ${PYTHON} -m pip install -r requirements.txt
                        '''
                    } else {
                        // Windows PowerShell
                        bat '''
                            ${PYTHON} -m venv ${VENV_DIR}
                            .\\${VENV_DIR}\\Scripts\\activate.bat
                            ${PYTHON} -m pip install --upgrade pip
                            ${PYTHON} -m pip install -r requirements.txt
                        '''
                    }
                }
            }
        }

        stage('Lint & Format Check') {
            steps {
                echo '====== Running pytest collection check ======'
                script {
                    if (isUnix()) {
                        sh '''
                            . ${VENV_DIR}/bin/activate
                            ${PYTHON} -m pytest tests/ --collect-only -q
                        '''
                    } else {
                        bat '''
                            .\\${VENV_DIR}\\Scripts\\activate.bat
                            ${PYTHON} -m pytest tests/ --collect-only -q
                        '''
                    }
                }
            }
        }

        stage('Run Tests') {
            steps {
                echo '====== Executing Pytest Suite (Headless Mode) ======'
                script {
                    if (isUnix()) {
                        sh '''
                            . ${VENV_DIR}/bin/activate
                            ${PYTHON} -m pytest tests/ \
                                -v \
                                --headless true \
                                --browser chrome \
                                --html=reports/report.html \
                                --self-contained-html \
                                --junitxml=reports/junit.xml \
                                --tb=short \
                                || true
                        '''
                    } else {
                        // Windows
                        bat '''
                            .\\${VENV_DIR}\\Scripts\\activate.bat
                            ${PYTHON} -m pytest tests/ ^
                                -v ^
                                --headless true ^
                                --browser chrome ^
                                --html=reports/report.html ^
                                --self-contained-html ^
                                --junitxml=reports/junit.xml ^
                                --tb=short ^
                                || exit /b 0
                        '''
                    }
                }
            }
        }

        stage('Generate Reports') {
            steps {
                echo '====== Archiving Test Reports ======'
                // HTML Report
                publishHTML([
                    reportDir: 'reports',
                    reportFiles: 'report.html',
                    reportName: 'Pytest HTML Report',
                    keepAll: true,
                    alwaysLinkToLastBuild: true
                ])

                // Screenshots Gallery (if exists)
                publishHTML([
                    reportDir: 'reports',
                    reportFiles: 'locale_gallery.html',
                    reportName: 'Locale Screenshots Gallery',
                    keepAll: true,
                    alwaysLinkToLastBuild: false
                ])
            }
        }

        stage('Publish JUnit Results') {
            steps {
                echo '====== Publishing JUnit Test Results ======'
                junit testResults: 'reports/junit.xml', 
                      allowEmptyResults: true,
                      keepLongStdio: true
            }
        }
    }

    post {
        always {
            echo '====== Pipeline Completed ======'
            archiveArtifacts artifacts: 'reports/**', 
                             allowEmptyArchive: true
            cleanWs()
        }

        success {
            echo '✓ All tests passed!'
        }

        failure {
            echo '✗ Some tests failed. Check reports for details.'
        }

        unstable {
            echo '⚠ Pipeline unstable. Review test results.'
        }
    }
}
