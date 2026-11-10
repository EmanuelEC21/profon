# Preenche planejamentos no Word e exporta em PDF.
# Uso (chamado por scripts/gerar_planejamento.py): powershell -File preencher_planejamento.ps1 tarefas.json
param([Parameter(Mandatory = $true)][string]$Tarefas)

$ErrorActionPreference = "Stop"
$lista = Get-Content -Raw -Encoding UTF8 $Tarefas | ConvertFrom-Json
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0

function Normalizar([string]$t) {
    return (($t -replace "[\r\a\v:]", " ") -replace "\s+", " ").Trim().ToUpper()
}

try {
    foreach ($t in $lista) {
        New-Item -ItemType Directory -Force (Split-Path $t.docx) | Out-Null
        New-Item -ItemType Directory -Force (Split-Path $t.copia_pdf) | Out-Null
        $doc = $word.Documents.Open($t.modelo, $false, $true)   # abre o modelo só para leitura
        $doc.SaveAs2($t.docx, 16)                              # 16 = docx; daqui em diante edita a cópia
        $preenchidos = 0
        foreach ($cell in $doc.Tables.Item(1).Range.Cells) {
            $rotulo = Normalizar $cell.Range.Paragraphs.Item(1).Range.Text
            foreach ($campo in $t.campos.PSObject.Properties) {
                if ($rotulo -eq (Normalizar $campo.Name)) {
                    # Mantém o parágrafo do rótulo e deixa um único parágrafo de conteúdo.
                    while ($cell.Range.Paragraphs.Count -gt 2) { $cell.Range.Paragraphs.Last.Range.Delete() | Out-Null }
                    if ($cell.Range.Paragraphs.Count -lt 2) { $cell.Range.Paragraphs.Item(1).Range.InsertParagraphAfter() }
                    $r = $cell.Range.Paragraphs.Item(2).Range
                    $r.MoveEnd(1, -1) | Out-Null                        # sem a marca de fim de célula
                    $r.Text = ($campo.Value -replace "`n", [string][char]11)  # várias linhas = quebra manual
                    $r.Font.Bold = $false
                    $preenchidos++
                }
            }
        }
        if ($preenchidos -ne $t.campos.PSObject.Properties.Name.Count) {
            throw "Só $preenchidos campos encontrados no modelo $($t.modelo)."
        }
        $doc.Save()
        $doc.ExportAsFixedFormat($t.pdf, 17)                       # 17 = PDF
        $doc.Close($false)
        Copy-Item -Force $t.pdf $t.copia_pdf
        Write-Output "OK  $($t.pdf)"
    }
}
finally {
    $word.Quit()
}
