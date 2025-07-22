{{- define "web.pod" -}}
{{- $root := . -}}
{{- with .Values.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
serviceAccountName: {{ include "gopie-web.serviceAccountName" . }}
securityContext:
  {{- toYaml .Values.web.podSecurityContext | nindent 2 }}
containers:
  - name: {{ .Chart.Name }}
    securityContext:
      {{- toYaml .Values.web.securityContext | nindent 6 }}
    image: "{{ .Values.web.image.repository | default .Values.web.image.repository }}:{{ .Values.web.image.tag | default .Values.web.image.tag | default .Chart.AppVersion }}"
    imagePullPolicy: {{ .Values.web.image.pullPolicy | default .Values.web.image.pullPolicy }}
    ports:
      - name: {{ .Values.web.service.portName }}
        containerPort: {{ .Values.web.service.portNumber }}
        protocol: TCP
    livenessProbe:
      {{- toYaml .Values.web.livenessProbe | nindent 6 }}
    readinessProbe:
      {{- toYaml .Values.web.readinessProbe | nindent 6 }}
    {{- if .Values.web.env }}
    {{- with .Values.web.env }}
    env:
    {{- toYaml . | nindent 6 }}
    {{- end }}
    {{- end }}
    resources:
      {{- toYaml .Values.web.resources | nindent 6 }}
    volumeMounts:
      {{- range .Values.web.extraVolumeMounts }}
      - name: {{ .name }}
        mountPath: {{ .mountPath }}
        subPath: {{ .subPath | default "" }}
        readOnly: {{ .readOnly }}
      {{- end }}
{{- with .Values.web.nodeSelector }}
nodeSelector:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.web.affinity }}
affinity:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.web.tolerations }}
tolerations:
  {{- toYaml . | nindent 2 }}
{{- end }}
volumes:
  {{- toYaml .Values.web.volumes | nindent 6 }}
{{- end }}