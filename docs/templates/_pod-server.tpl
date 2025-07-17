{{- define "server.pod" -}}
{{- $root := . -}}
{{- with .Values.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
serviceAccountName: {{ include "server.serviceAccountName" . }}
securityContext:
  {{- toYaml .Values.server.podSecurityContext | nindent 2 }}
{{- if .Values.server.initContainers }}
initContainers:
{{- range .Values.server.initContainers }}
  - name: {{ .name }}
    image: {{ .image }}
    imagePullPolicy: {{ .imagePullPolicy | default "IfNotPresent" }}
    command: {{- toYaml .command | nindent 6 }}
    args: {{- toYaml .args | nindent 6 }}
    env:
      {{- toYaml .env | nindent 6 }}
    volumeMounts:
      {{- range .volumeMounts }}
      - name: {{ .name }}
        mountPath: {{ .mountPath }}
        subPath: {{ .subPath | default "" }}
        readOnly: {{ .readOnly | default false }}
      {{- end }}
{{- end }}
{{- end }}
containers:
  - name: {{ include "server.name" . }}
    securityContext:
      {{- toYaml .Values.server.securityContext | nindent 6 }}
    image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
    imagePullPolicy: {{ .Values.image.pullPolicy }}
    ports:
      - name: {{ .Values.server.service.portName }}
        containerPort: {{ .Values.server.service.portNumber }}
        protocol: TCP
    livenessProbe:
      {{- toYaml .Values.server.livenessProbe | nindent 6 }}
    readinessProbe:
      {{- toYaml .Values.server.readinessProbe | nindent 6 }}
    {{- if .Values.server.env }}
    {{- with .Values.server.env }}
    env:
      - name: GOPIE_POSTGRES_HOST
        value: {{ printf "%s-postgresql" $root.Release.Name | quote }}
      - name: GOPIE_POSTGRES_DB
        value: {{ $root.Values.postgresql.auth.database }}
      - name: GOPIE_POSTGRES_USER
        value: {{ $root.Values.postgresql.auth.username }}
      - name: GOPIE_POSTGRES_PASSWORD
        valueFrom:
          secretKeyRef:
            name: {{ printf "%s-postgresql" $root.Release.Name }}
            key: postgresql-password
    {{- toYaml . | nindent 6 }}
    {{- end }}
    {{- end }}
    resources:
      {{- toYaml .Values.server.resources | nindent 6 }}
    volumeMounts:
      {{- range .Values.server.extraVolumeMounts }}
      - name: {{ .name }}
        mountPath: {{ .mountPath }}
        subPath: {{ .subPath | default "" }}
        readOnly: {{ .readOnly }}
      {{- end }}
{{- with .Values.server.nodeSelector }}
nodeSelector:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.server.affinity }}
affinity:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.server.tolerations }}
tolerations:
  {{- toYaml . | nindent 2 }}
{{- end }}
volumes:
  
  {{- if and .Values.server.persistence.enabled (eq .Values.server.persistence.type "pvc") }}
  - name: store
    persistentVolumeClaim:
      claimName: {{ tpl (.Values.server.persistence.existingClaim | default (include "server.name" .)) . }}
  {{- else }}
  - name: store
    {{- if .Values.server.persistence.inMemory.enabled }}
    emptyDir:
      medium: Memory
      {{- with .Values.server.persistence.inMemory.sizeLimit }}
      sizeLimit: {{ . }}
      {{- end }}
    {{- else }}
    emptyDir: {}
    {{- end }}
  {{- end }}
  {{- range .Values.server.extraVolumes }}
  - name: {{ .name }}
    {{- if .existingClaim }}
    persistentVolumeClaim:
      claimName: {{ .existingClaim }}
    {{- else if .hostPath }}
    hostPath:
      {{ toYaml .hostPath }}
    {{- else if .csi }}
    csi:
      {{- toYaml .csi }}
    {{- else if .configMap }}
    configMap:
      {{- toYaml .configMap }}
    {{- else if .secret }}
    secret:
      {{- toYaml .secret | nindent 4 }}
    {{- else if .emptyDir }}
    emptyDir:
      {{- toYaml .emptyDir }}
    {{- else }}
    emptyDir: {}
    {{- end }}
  {{- end }}
 {{- end }}