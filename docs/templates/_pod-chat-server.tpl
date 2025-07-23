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
    {{- if .Values.chatserver.env }}
    {{- with .Values.chatserver.env }}
    env:
    {{- toYaml . | nindent 6 }}
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