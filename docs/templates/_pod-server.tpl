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
    {{- if .command }}
    command: {{- toYaml .command | nindent 6 }}
    {{- end }}
    {{- if .args }}
    args: {{- toYaml .args | nindent 6 }}
    {{- end }}
    env:
      - name: GOOSE_DBSTRING
        valueFrom:
          secretKeyRef:
            name: {{ include "gopie.fullname" $root }}-goose
            key: goose-dbstring-template
      - name: POSTGRES_PASSWORD
        valueFrom:
          secretKeyRef:
            name: {{ printf "%s-postgresql" $root.Release.Name }}
            key: postgres-password
      {{- if .env }}
      {{- range .env }}
      - name: {{ .name }}
        value: {{ .value | quote }}
      {{- end }}
      {{- end }}
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
      {{- range .Values.service.ports }}
      - name: {{ .name }}
        containerPort: {{ .port }}
        protocol: {{ .protocol }}
      {{- end }}
    {{- if .Values.deployment.livenessProbe }}
    livenessProbe:
      {{- toYaml .Values.deployment.livenessProbe | nindent 6 }}
    {{- end }}
    {{- if .Values.deployment.readinessProbe }}
    readinessProbe:
      {{- toYaml .Values.deployment.readinessProbe | nindent 6 }}
    {{- end }}
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
            key: postgres-password
      - name: GOPIE_S3_ACCESS_KEY
        valueFrom:
          secretKeyRef:
            name: {{ printf "%s-minio" $root.Release.Name }}
            key: root-user
      - name: GOPIE_S3_SECRET_KEY
        valueFrom:
          secretKeyRef:
            name: {{ printf "%s-minio" $root.Release.Name }}
            key: root-password
      - name: GOPIE_S3_ENDPOINT
        value: {{ printf "http://%s-minio:9000" $root.Release.Name }}
      - name: GOPIE_S3_SSL
        value: {{ $root.Values.minio.tls.enabled | default "false" | quote }}
      - name: GOPIE_S3_REGION
        value: {{ $root.Values.minio.region | default "us-east-1" }}
      - name: GOPIE_AIAGENT_URL
        value: {{ printf "http://%s-chatserver:%v" $root.Release.Name ($root.Values.chatserver.service.portNumber | default 8000) }}
    {{- if .Values.deployment.env }}
    {{- range .Values.deployment.env }}
      - name: {{ .name }}
        value: {{ .value | quote }}
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
      {{- range .Values.service.ports }}
      - name: {{ .name }}
        containerPort: {{ .port }}
        protocol: TCP
      {{- end }}
    {{- if .Values.stateful.livenessProbe }}
    livenessProbe:
      {{- toYaml .Values.stateful.livenessProbe | nindent 6 }}
    {{- end }}
    {{- if .Values.stateful.readinessProbe }}
    readinessProbe:
      {{- toYaml .Values.stateful.readinessProbe | nindent 6 }}
    {{- end }}
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
            key: postgres-password
      - name: GOPIE_S3_ACCESS_KEY
        valueFrom:
          secretKeyRef:
            name: {{ printf "%s-minio" $root.Release.Name }}
            key: root-user
      - name: GOPIE_S3_SECRET_KEY
        valueFrom:
          secretKeyRef:
            name: {{ printf "%s-minio" $root.Release.Name }}
            key: root-password
      - name: GOPIE_S3_ENDPOINT
        value: {{ printf "http://%s-minio:9000" $root.Release.Name }}
      - name: GOPIE_S3_SSL
        value: {{ $root.Values.minio.tls.enabled | default "false" | quote }}
      - name: GOPIE_S3_REGION
        value: {{ $root.Values.minio.region | default "us-east-1" }}
      - name: GOPIE_AIAGENT_URL
        value: {{ printf "http://%s-chatserver:%v" $root.Release.Name ($root.Values.chatserver.service.portNumber | default 8000) }}
    {{- if .Values.stateful.env }}
    {{- range .Values.stateful.env }}
      - name: {{ .name }}
        value: {{ .value | quote }}
    {{- end }}
    {{- end }}
    resources: {{- toYaml .Values.stateful.resources | nindent 6 }}
    volumeMounts:
      {{- range .Values.deployment.extraVolumeMounts }}
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