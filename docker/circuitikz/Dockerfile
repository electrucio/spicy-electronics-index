# TeX Live with circuitikz and dvisvgm: the bench circuit drawings, typeset by LaTeX and exported as SVG with the
# text as paths, so that every browser shows the same page. Build once: make circuitikz-image
FROM debian:bookworm-slim
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      texlive-latex-base texlive-latex-recommended texlive-latex-extra texlive-pictures texlive-fonts-recommended \
      dvisvgm ghostscript && rm -rf /var/lib/apt/lists/*
WORKDIR /w
