all:run-fusion

run-fusion:
	docker run --rm --name fusion \
	    -v /mnt/data:/data \
            jpfeil/star-fusion:0.0.2 \
            --left_fq samples/{} --right_fq samples/{} --output_dir outputs/fusion \
            --CPU `nproc` \
            --genome_lib_dir references/STARFusion-GRCh38gencode23 \
            --run_fusion_inspector
