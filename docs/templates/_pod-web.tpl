{{- define "web.pod" -}}
{{- $root := . -}}
{{- with .Values.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
serviceAccountName: {{ include "web.serviceAccountName" . }}
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
    {{- if .Values.web.livenessProbe }}
    livenessProbe:
      {{- toYaml .Values.web.livenessProbe | nindent 6 }}
    {{- end }}
    {{- if .Values.web.readinessProbe }}
    readinessProbe:
      {{- toYaml .Values.web.readinessProbe | nindent 6 }}
    {{- end }}
    env:
      - name: GOPIE_API_URL
        value: {{ printf "http://%s-server:%v" .Release.Name (.Values.service.portNumber | default 8000) }}
    {{- if .Values.web.env }}
    {{- range .Values.web.env }}
      - name: {{ .name }}
        value: {{ .value | quote }}
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