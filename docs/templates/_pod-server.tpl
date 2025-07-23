{{- define "deployment.pod" -}}
{{- $root := . -}}
{{- with .Values.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
serviceAccountName: {{ include "server.serviceAccountName" . }}
securityContext:
  {{- toYaml .Values.deployment.podSecurityContext | nindent 2 }}
{{- if .Values.deployment.initContainers }}
initContainers:
{{- range .Values.deployment.initContainers }}
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
      {{- toYaml .Values.deployment.securityContext | nindent 6 }}
    image: "{{ .Values.deployment.image.repository }}:{{ .Values.deployment.image.tag | default .Chart.AppVersion }}"
    imagePullPolicy: {{ .Values.deployment.image.pullPolicy }}
    ports:
      - name: {{ .Values.service.portName }}
        containerPort: {{ .Values.service.portNumber }}
        protocol: TCP
    {{- if .Values.deployment.livenessProbe }}
    livenessProbe:
      {{- toYaml .Values.deployment.livenessProbe | nindent 6 }}
    {{- end }}
    {{- if .Values.deployment.readinessProbe }}
    readinessProbe:
      {{- toYaml .Values.deployment.readinessProbe | nindent 6 }}
    {{- end }}
    {{- if .Values.deployment.env }}
    {{- with .Values.deployment.env }}
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
      {{- toYaml .Values.deployment.resources | nindent 6 }}
    volumeMounts:
      {{- range .Values.deployment.extraVolumeMounts }}
      - name: {{ .name }}
        mountPath: {{ .mountPath }}
        subPath: {{ .subPath | default "" }}
        readOnly: {{ .readOnly }}
      {{- end }}
{{- with .Values.deployment.nodeSelector }}
nodeSelector:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.deployment.affinity }}
affinity:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.deployment.tolerations }}
tolerations:
  {{- toYaml . | nindent 2 }}
{{- end }}
volumes:
  {{- toYaml .Values.deployment.volumes | nindent 6 }}
 {{- end }}








{{- define "stateful.pod" -}}
{{- $root := . -}}
{{- with .Values.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
serviceAccountName: {{ include "server.serviceAccountName" . }}
securityContext:
  {{- toYaml .Values.stateful.podSecurityContext | nindent 2 }}
{{- if .Values.stateful.initContainers }}
initContainers:
{{- range .Values.stateful.initContainers }}
  - name: {{ .name }}
    image: {{ .image }}
    imagePullPolicy: {{ .imagePullPolicy | default "IfNotPresent" }}
    command: {{- toYaml .command | nindent 8 }}
    env:
      {{- toYaml .env | nindent 8 }}
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
  - name: {{ .Chart.Name }}
    securityContext:
      {{- toYaml .Values.stateful.securityContext | nindent 6 }}
    image: "{{ .Values.stateful.image.repository }}:{{ .Values.stateful.image.tag | default .Chart.AppVersion }}"
    imagePullPolicy: {{ .Values.stateful.image.pullPolicy }}
    ports:
      - name: {{ .Values.service.portName }}
        containerPort: {{ .Values.service.portNumber }}
        protocol: TCP
    {{- if .Values.stateful.livenessProbe }}
    livenessProbe:
      {{- toYaml .Values.stateful.livenessProbe | nindent 6 }}
    {{- end }}
    {{- if .Values.stateful.readinessProbe }}
    readinessProbe:
      {{- toYaml .Values.stateful.readinessProbe | nindent 6 }}
    {{- end }}
    {{- if .Values.stateful.env }}
    {{- with .Values.stateful.env }}
    env:
    {{- toYaml . | nindent 6 }}
    {{- end }}
    {{- end }}
    resources:
      {{- toYaml .Values.stateful.resources | nindent 6 }}
    volumeMounts:
      {{- range .Values.stateful.extraVolumeMounts }}
      - name: {{ .name }}
        mountPath: {{ .mountPath }}
        subPath: {{ .subPath | default "" }}
        readOnly: {{ .readOnly }}
      {{- end }}
{{- with .Values.stateful.nodeSelector }}
nodeSelector:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.stateful.affinity }}
affinity:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.stateful.tolerations }}
tolerations:
  {{- toYaml . | nindent 2 }}
{{- end }}
volumes:
  {{- if and .Values.stateful.persistence.enabled (eq .Values.stateful.persistence.type "pvc") }}
  - name: storage
    persistentVolumeClaim:
      claimName: {{ tpl (.Values.stateful.persistence.existingClaim | default (include "server.name" .)) . }}
  {{- else }}
  - name: storage
    {{- if .Values.stateful.persistence.inMemory.enabled }}
    emptyDir:
      medium: Memory
      {{- with .Values.stateful.persistence.inMemory.sizeLimit }}
      sizeLimit: {{ . }}
      {{- end }}
    {{- else }}
    emptyDir: {}
    {{- end }}
  {{- end }}
  {{- range .Values.stateful.extraVolumes }}
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
      {{- toYaml .secret }}
    {{- else if .emptyDir }}
    emptyDir:
      {{- toYaml .emptyDir }}
    {{- else }}
    emptyDir: {}
    {{- end }}
  {{- end }}
{{- end }}