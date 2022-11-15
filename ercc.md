# ERCC transcript-enabled pipeline
October 27, 2022

[Treeshop](treeshop.md) can now be run to process fastq files which contain ERCC transcripts.
This path will run only the MD5sum, expression, and QC steps.
It creates differently-named outputs so it can be run "on top" of an ERCC-unaware output directory.

### How to run
Follow [the Treeshop guidelines](treeshop.md) to create one or more virtual machines with `fab up`, `fab configure`. 
However, instead of running `fab reference`, run `fab reference_ercc`. This will download the ERCC-aware reference files.

Then, when you run `fab process`, include the flag `ercc=True` to indicate that the ERCC-aware path should be taken. For example:
```
fab process:manifest=manifest.tsv,base=/data/treehouse/allFiles,ercc=True
```
All samples listed in your manifest will be run under the ERCC-aware path; you cannot mix ERCC and non-ERCC in a single `fab process`.

### Output files and directories
The ERCC-aware process's outputs are named differently from the standard pipeline so that they can coexist.

Under `primary/derived/SAMPLE`, the files:
```
sortedByCoord.md.ERCC.bam
sortedByCoord.md.ERCC.bam.bai
```

Under `downstream/SAMPLE/secondary`, the dirs:
```
md5sum-ERCC-3.7.0-ccba511
ucsc_cgl-rnaseq-cgl-pipeline-ERCC-3.3.4-785eee9
ucsctreehouse-bam-mend-qc-ERCC-v2.0.2-1c3c627
```
And the files in `ucsctreehouse-bam-mend-qc-ERCC-v2.0.2-1c3c627` are:
```
bam_mend_qc.json
bam_mend_qc.tsv
methods.json
readDist.txt
```
(Other directories have the same file names as their non-ERCC counterparts.)
### Known Problems
- The `Kallisto/abundance.tsv` file has numbers 1,2,3 etc for its targets instead of the intended gene or transcript IDs.
- The `RSEM/Hugo/rsem_genes.hugo.results` file is bad in some way that I have not investigated: it has 60,449 rows but should have 92 extra 
due to the ERCC transcripts. (Compare `RSEM/rsem_genes.results`, which has 60,591 rows instead of the standard 60,499). Use with caution.
- When the `fusions` step was run, it crashed on every ERCC sample attempted and did not generate fusions.

### How to use existing virtual machines
If you have already spun up one or more virtual machines using fab for a non-ERCC run, you can reuse those machines (once idle) for an ERCC run.
To do this, run `fab reference_ercc` once to download the ERCC reference files onto the machines.
Then, continue with `fab process:ercc=True,manifest=...etc` as above.

