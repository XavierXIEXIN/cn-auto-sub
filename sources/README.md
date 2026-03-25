# Sources

Public upstream subscriptions live in `public-subs.txt`.

Public remote list files live in `public-remote-lists.txt`.

Private HTTP/HTTPS subscription URLs should stay out of git and be stored in the GitHub Actions secret `PRIVATE_SUB_URLS` as newline-separated entries.

Private mixed subscription content, such as a multiline export containing direct `vless://` or `ss://` nodes, should be stored in the `PRIVATE_SUB_CONTENT` secret. The workflow serves it on a runner-local HTTP endpoint during execution so it never needs to be committed publicly.

Optional private remote list URLs can be stored in the `PRIVATE_REMOTE_LISTS` secret, also newline-separated.
