pipeline {
    agent any

    options {
        timeout(time: 45, unit: 'MINUTES')
    }

    parameters {
        choice(name: 'VERSION_ESCANEO', choices: ['vulnerable', 'corregida'],
               description: 'Versión del código que escaneará OWASP ZAP')
    }

    environment {
        DEPLOY_DIR = "/var/jenkins_home/app-deploy"
        VENV_NAME = "venv"
        VULN_COMMIT = "6fa57f1"
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

        stage('4. Test - Pruebas de seguridad (ZAP)') {
            steps {
                echo "==> [Jenkins] OWASP ZAP: escaneando la versión ${params.VERSION_ESCANEO}"
                sh '''
                    . ${VENV_NAME}/bin/activate
                    rm -rf scan && mkdir scan
                    if [ "${VERSION_ESCANEO}" = "vulnerable" ]; then
                        git show ${VULN_COMMIT}:app.py > scan/app.py
                        git show ${VULN_COMMIT}:init_db.py > scan/init_db.py
                        FLASK_OPTS="--debug --no-reload"
                    else
                        cp app.py init_db.py scan/
                        FLASK_OPTS=""
                    fi

                    cd scan
                    python init_db.py
                    flask --app app run --port 5000 ${FLASK_OPTS} > ../app.log 2>&1 < /dev/null &
                    echo $! > ../app.pid
                    cd ..

                    for i in $(seq 1 20); do
                        curl -s -o /dev/null http://127.0.0.1:5000/login && break
                        sleep 1
                    done
                    echo "Aplicación lista, HTTP $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/login)"

                    docker rm -f zap-scan || true
                    docker run --name zap-scan --user root --network container:jenkins \
                        ghcr.io/zaproxy/zaproxy:stable \
                        sh -c "mkdir -p /zap/wrk && zap-full-scan.py -t http://127.0.0.1:5000 -m 2 -I -r zap-report.html" || true
                    docker cp zap-scan:/zap/wrk/zap-report.html zap-report-${VERSION_ESCANEO}.html
                    docker rm zap-scan

                    kill $(cat app.pid) || true
                '''
            }
        }

        stage('5. Deploy') {
            when {
                expression { params.VERSION_ESCANEO == 'corregida' }
            }
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
        always {
            sh '[ -f app.pid ] && kill $(cat app.pid) || true'
            sh 'docker rm -f zap-scan || true'
            archiveArtifacts artifacts: 'zap-report-*.html, app.log', allowEmptyArchive: true
        }
        success {
            echo "¡El build finalizó correctamente!"
        }
        failure {
            echo "El pipeline falló durante la ejecución."
        }
    }
}
