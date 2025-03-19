### DockerHub Watcher

A simple flask app that can be used as liveness check in Kubernetes to check if a DockerHub image of a container was updated.

### Usage

```yaml

      containers:
        - name: watcher
          image: xarthisius/dhwatcher:latest
          envFrom:
            - secretRef:
                name: dockerhub-creds
          env:
            - name: POD_NAME
              value: {{ .Chart.Name }}
            - name: POD_NAMESPACE
              value: {{ .Release.Namespace }}
          ports:
            - containerPort: 8081
          resources:
            limits:
              cpu: 100m
              ephemeral-storage: 2Mi
              memory: 256Mi
            requests:
              cpu: 100m
              ephemeral-storage: 1Mi
              memory: 128Mi
          securityContext:
            allowPrivilegeEscalation: false
            runAsNonRoot: true
            capabilities:
              drop: ["ALL"]
        - name: {{ .Chart.Name }}
          ...
          livenessProbe:
            httpGet:
              path: /health
              port: 8081
            initialDelaySeconds: 10
            periodSeconds: 60
            failureThreshold: 1
            timeoutSeconds: 10
```
