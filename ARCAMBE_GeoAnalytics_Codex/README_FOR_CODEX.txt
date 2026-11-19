ARCAMBE GEOANALYTICS — INSTRUÇÕES PARA ENTREGA AO CODEX

1. Extraia o ZIP para a pasta de um repositório novo.
2. Abra essa pasta no Codex.
3. Copie e cole o conteúdo de CODEX_MASTER_PROMPT.md como tarefa inicial.
4. Diga explicitamente ao Codex para ler todos os ficheiros e criar implementação funcional; não apenas mockups.
5. Reforce que os 21 índices do ficheiro contracts/spectral_indices.yaml são obrigatórios, além de band ratio, temporal difference, PCA e RGB/FCC.
6. Entregue credenciais Firebase/GCP/fornecedor de imagens via Secret Manager ou ficheiro .env local privado, nunca partilhando senhas nesta conversa ou no Git.
7. Exija relatórios de testes e evidências de processamento raster real antes de considerar concluído.
8. O manual enviado menciona explicitamente NDVI (p.159), razão espectral, diferença temporal e PCA; os 20 restantes índices foram acrescentados como extensão técnica, não extraídos da lista do manual.
