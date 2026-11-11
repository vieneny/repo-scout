# Match evaluation to the intended outcome

Use only the relevant scenario below. Keep the same seven scoring criteria and assessment schema; these checks explain the evidence behind `strengths`, `gaps`, `learning_path`, and optional sourced `usage_requirements`. Unknown requirements remain unknown.

## Java graduation projects and business applications

For a brief such as “找一下学习 Java 的毕设设计项目”, seek manageable applications with readable business flows, not only framework lists or interview exercises. Unless the user specifies a domain, search across several useful domains such as booking, inventory, campus services, or content management. Treat domains as alternatives, not a requirement to return all of them.

Inspect the path from user action through service logic to persistent data and visible result. Establish the actual stack from manifests and configuration: Java/framework versions, frontend, database, build tools, and any middleware. Distinguish a complete application from an API skeleton, a screenshot collection, or a frontend using mock data.

Evaluate what one student can understand, demonstrate, and extend: setup instructions, database schema/seed data, realistic roles and operations, module boundaries, examples, tests where relevant, and a concrete extension path. Source code, database use, and feature evidence must support the claimed flow. Missing setup evidence is a gap; an SQL file alone does not prove the application starts.

A large enterprise system receives no automatic bonus. Explain its learning cost when distributed services, infrastructure, or generated code overshadow the business flow. A smaller project can be the best reference. Keep academic reuse and attribution visible; recommending a repository is not a claim that submitting its code satisfies the user's institution rules.

## AI image and art tools

Separate the requested workflow: generating from text, editing an input image, inpainting, reference/identity control, upscaling, or managing a generation workflow. Inspect input handling, processing pipeline and model dependencies, and output/export behavior. A model repository, UI shell, hosted client, and self-contained application solve different parts of that path.

Check installation, supported operating systems, local versus cloud execution, model download/access, external APIs and documented costs. Record GPU/VRAM, CPU/RAM/disk, runtime or acceleration requirements when relevant and evidenced. Do not infer a hardware minimum from model family or a screenshot.

Use sample outputs as attributed examples, identifying whether they come from maintainers, users, or your own authorized test. A gallery shows claimed sample quality; it does not establish reproducibility, speed, or consistent quality on the user's inputs. Distinguish code licensing from model-weight, dataset, asset, and hosted-service terms, including restrictions affecting reuse or commercial output.

## Video generation, animation, and editing

Identify whether the goal is text-to-video, image-to-video, video-to-video, editing existing clips, captions, compositing, or a combined workflow. Search the appropriate tool class and trace input → model/processing → export. Inspect required models, extensions, system tools, file formats, and any documented output constraints such as duration, resolution, frame rate, or watermarking.

Check local/cloud operation, hardware and storage requirements, model access, API/service costs, and reproducible examples. Keep documented capabilities separate from measured results. A polished demo does not verify generation speed, temporal consistency, or output quality for the user's material. Review code and non-code terms separately as for image tools.

## Audio, writing, and other tools

Define the concrete input and desired output before searching. For audio, separate speech synthesis, transcription, voice conversion, music generation, and editing; relevant constraints can include language, model access, hardware, output formats, and voice/model terms. For writing, distinguish a local editor, a workflow application, an agent, and a hosted-model client; inspect storage/export, provider requirements, and external cost.

For other tool categories, use the same evidence path: input → processing/model/dependencies → output, then operating requirements, usable examples, maintained source, and reuse terms. Add category-specific constraints only when they affect the user's decision. This workflow finds and compares tools; it does not itself authorize generating media, uploading user material to services, or executing discovered code.

## Show the decision clearly

For each leading candidate, explain what the user can learn or produce, where to begin in the source, what setup or resource burden is established, and what remains unverified. Link the source behind practical requirements. Use `learning_path` for a short reading/extension route, `strengths` for evidenced advantages, and `gaps` for missing paths or conflicts. Optional `usage_requirements` can surface sourced operating requirements without adding a new mandatory scenario schema. Apply the user's constraints before treating popularity as a tie-breaker.
