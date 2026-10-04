FROM barichello/godot-ci:4.4.1 AS build

WORKDIR /project

COPY . .

RUN mkdir -p export-web export-linux

RUN godot --headless --path /project --export-release "Web" /project/export-web/index.html \
 && godot --headless --path /project --export-release "Linux" /project/export-linux/pico-walk.x86_64


FROM debian:trixie-slim AS runtime

WORKDIR /game

COPY --from=build /project/export-web ./export-web
COPY --from=build /project/export-linux ./export-linux

#ENTRYPOINT ["/bin/bash", "-c", "/game/export-linux/pico-walk.x86_64 --headless --server"]
ENTRYPOINT ["/game/export-linux/pico-walk.x86_64", "--headless", "--server"]
