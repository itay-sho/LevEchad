#!/bin/sh -l

# Get args
readonly LINTER_ARGS=$1
readonly COMMENT_MESSAGE=$2

readonly MARKDOWN_CODE_WRAPPER='```'
cd $GITHUB_WORKSPACE

# Replace newlines with line break
# sed explained:
#    'a:' label named "a"
#    'N' Append the next line to the pattern (<br />)
#    '$!' if not the last line 'ba' branch (goto) label a
#    's' substitue
pycode_output=$(python -m pycodestyle ${LINTER_ARGS} . | sed ':a;N;$!ba;s/\n/<br \/>/g')

comment="{\"body\": \"${COMMENT_MESSAGE}<br />${MARKDOWN_CODE_WRAPPER}${pycode_output}${MARKDOWN_CODE_WRAPPER}\"}"
echo -En ${comment} > payload.json
cat payload.json

# Escape backslashes if any
sed -i 's#\\#\\\\#g' payload.json

# Endpoint for posting comments
comments_endpoint=$(cat ${GITHUB_EVENT_PATH} | jq -r .pull_request.comments_url)

curl -sS -H "Authorization: token ${GITHUB_TOKEN}" -H "Content-Type: Application/json" --data-binary @payload.json ${comments_endpoint}

exit 0

