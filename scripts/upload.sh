#!/bin/bash
# Send one clip to a Notion file upload that notion-create-file-upload just created.
# usage: upload.sh <workdir> <clip e.g. Day4-01> <upload_url> <authorization header value>
# On success appends "clip<TAB>file_upload_id" to <workdir>/uploads.tsv.
work="$1"; clip="$2"; url="$3"; auth="$4"
f="${work}/clips/${clip}.mp3"
[ -f "$f" ] || { echo "MISSING FILE $f"; exit 1; }
id=$(echo "$url" | sed -E 's#.*/file_uploads/([^/]+)/send.*#\1#')
out=$(curl -s -m 90 -X POST "$url" -H "authorization: ${auth}" --form "file=@${f};type=audio/mpeg")
if echo "$out" | grep -q '"status":"uploaded"'; then
  touch "${work}/uploads.tsv"
  grep -v "^${clip}	" "${work}/uploads.tsv" > "${work}/uploads.tmp"; mv "${work}/uploads.tmp" "${work}/uploads.tsv"
  printf "%s\t%s\n" "$clip" "$id" >> "${work}/uploads.tsv"; echo "OK $clip"
else echo "FAIL $clip: $out"; exit 1; fi
