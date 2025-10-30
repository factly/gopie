{{- define "chatserver.pod" -}}
{{- $root := . -}}
{{- with .Values.chatserver.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
serviceAccountName: {{ include "chatserver.serviceAccountName" . }}
securityContext:
  {{- toYaml .Values.chatserver.podSecurityContext | nindent 2 }}
containers:
  - name: {{ .Chart.Name }}
    securityContext:
      {{- toYaml .Values.chatserver.securityContext | nindent 6 }}
    image: "{{ .Values.chatserver.image.repository }}:{{ .Values.chatserver.image.tag | default .Chart.AppVersion }}"
    imagePullPolicy: {{ .Values.chatserver.image.pullPolicy }}
    ports:
      - name: {{ .Values.chatserver.service.portName }}
        containerPort: {{ .Values.chatserver.service.portNumber }}
        protocol: TCP
    command: ["/bin/sh"]
    args: ["-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000"]
    {{- if .Values.chatserver.livenessProbe }}
    livenessProbe:
      {{- toYaml .Values.chatserver.livenessProbe | nindent 6 }}
    {{- end }}
    {{- if .Values.chatserver.readinessProbe }}
    readinessProbe:
      {{- toYaml .Values.chatserver.readinessProbe | nindent 6 }}
    {{- end }}
    env:
      - name: S3_HOST
        value: minio
      - name: S3_ACCESS_KEY
        valueFrom:
          secretKeyRef:
            name: {{ printf "%s-minio" .Release.Name }}
            key: root-user
      - name: S3_SECRET_KEY
        valueFrom:
          secretKeyRef:
            name: {{ printf "%s-minio" .Release.Name }}
            key: root-password
      - name: S3_BUCKET
        value: {{ .Values.minio.defaultBuckets }}
      - name: S3_REGION
        value: {{ .Values.minio.region | default "us-east-1" }}
      - name: QDRANT_HOST
        value: {{ printf "%s-qdrant" .Release.Name }}
      - name: QDRANT_PORT
        value: {{ .Values.qdrant.service.port | default "6333" | quote }}
    {{- if .Values.chatserver.env }}
    {{- range .Values.chatserver.env }}
      - name: {{ .name }}
        value: {{ .value | quote }}
    {{- end }}
    {{- end }}
    resources:
      {{- toYaml .Values.chatserver.resources | nindent 6 }}
    volumeMounts:
      {{- range .Values.chatserver.extraVolumeMounts }}
      - name: {{ .name }}
        mountPath: {{ .mountPath }}
        subPath: {{ .subPath | default "" }}
        readOnly: {{ .readOnly }}
      {{- end }}
{{- with .Values.chatserver.nodeSelector }}
nodeSelector:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.chatserver.affinity }}
affinity:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.chatserver.tolerations }}
tolerations:
  {{- toYaml . | nindent 2 }}
{{- end }}
volumes:
  {{- toYaml .Values.chatserver.volumes | nindent 6 }}
{{- end }}