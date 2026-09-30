#!/bin/sh
# Baut Karos Image — aber nur aus einem sauberen, committeten, gepushten Stand.
#
# Ein Image aus einem schmutzigen Arbeitsbaum laeuft mit Code, den kein
# Repository kennt: was darauf geprueft wird, kann niemand wiederholen. Und
# ein Image aus einem Commit, den es nur hier gibt, traegt eine SHA, die ins
# Leere zeigt. Derselbe Riegel steht im Lehrplan-Dienst.
set -eu
cd "$(dirname "$0")"

if [ -n "$(git status --porcelain)" ]; then
  echo "ABBRUCH: Der Arbeitsbaum ist nicht sauber." >&2
  echo "Ein Image aus nicht committetem Code ist nicht reproduzierbar." >&2
  echo >&2
  git status --short >&2
  exit 2
fi

SHA=$(git rev-parse HEAD)

if ! git branch -r --contains "$SHA" | grep -q .; then
  echo "ABBRUCH: $SHA ist auf keinem Remote." >&2
  echo "Erst pushen, dann bauen — sonst zeigt die SHA im Image ins Leere." >&2
  exit 3
fi

echo "Baue aus $SHA"
docker compose -f docker-compose.yml -f docker-compose.build.yml \
  build --build-arg "KARO_GIT_SHA=$SHA" "$@"
echo "Fertig. Image-Stand: $SHA"
