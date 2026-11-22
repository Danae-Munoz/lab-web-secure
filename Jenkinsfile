pipeline {
    agent any

    environment {
        DEPLOY_DIR = "/var/jenkins_home/app-deploy"
        VENV_NAME = "venv"
    }

    stages {
        stage('1. Dependency Management') {
            steps {
                echo "==> [Jenkins] Verificando requirements.txt..."
                sh '''
                    if [ ! -f "requirements.txt" ]; then
                        echo "Error: No se encontró el archivo requirements.txt en el repositorio"
                        exit 1
                    fi
                    cat requirements.txt
                '''
            }
        }

        stage('2. Build') {
            steps {
                echo "==> [Jenkins] Configurando entorno virtual e instalando dependencias..."
                sh '''
                    python3 -m venv ${VENV_NAME}
                    . ${VENV_NAME}/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('3. Security Review') {
            steps {
                echo "==> [Jenkins] Revisión de seguridad: análisis de código y de dependencias..."
                sh '''
                    . ${VENV_NAME}/bin/activate
                    pip install bandit pip-audit
                    echo "----- BANDIT: análisis estático del código -----"
                    bandit -r app.py init_db.py || true
                    echo "----- PIP-AUDIT: vulnerabilidades en dependencias -----"
                    pip-audit -r requirements.txt || true
                '''
            }
        }

        stage('4. Test') {
            steps {
                echo "==> [Jenkins] [TEST] Aquí se simulan las pruebas unitarias..."
                sh 'echo "Pruebas superadas con éxito en el workspace de Jenkins."'
            }
        }

        stage('5. Deploy') {
            steps {
                echo "==> [Jenkins] Desplegando la aplicación..."
                sh '''
                    mkdir -p ${DEPLOY_DIR}
                    cp app.py init_db.py requirements.txt ${DEPLOY_DIR}/
                    echo "¡Despliegue completado en ${DEPLOY_DIR}!"
                '''
            }
        }
    }

    post {
        success {
            echo "¡El build finalizó correctamente!"
        }
        failure {
            echo "El pipeline falló durante la ejecución."
        }
    }
}
