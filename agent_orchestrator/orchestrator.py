"""Main pipeline orchestrator — runs all phases sequentially with resume support."""

import logging
import os
import sys

from agent_orchestrator.qwen_client import QwenClient
from shared.models.pipeline import PipelineState, Phase
from shared.models.story import Story
from script_generator.script_generator import generate_story
from image_generation.qwen_image_client import generate_references, generate_scene_images
from narration.cosyvoice_client import generate_narration
from narration.tts_manager import generate_narration_with_voice
from export_pipeline.html_exporter import export_html
from image_generation.image_registry import ImageRegistry

logger = logging.getLogger(__name__)


def run_pipeline(
    prompt: str,
    age_group: str = "kids",
    voice: str = "ethan",
    output_base: str = "stories",
    resume: bool = True,
) -> str:
    """Run the full Imaginate pipeline end-to-end.

    Args:
        prompt: User's story idea.
        age_group: "kids" or "adult".
        voice: Narration voice ("ethan", "serena", or "cherry").
        output_base: Base directory for story outputs.
        resume: Whether to check for existing state and resume.

    Returns:
        Path to the final HTML storybook file.
    """
    client = QwenClient()

    slug = ""
    story_dir = ""
    story: Story | None = None

    # Check for existing resume first by trying to find a matching directory
    if resume:
        for d in os.listdir(output_base) if os.path.isdir(output_base) else []:
            story_json = os.path.join(output_base, d, f"{d}_story.json")
            if os.path.exists(story_json):
                try:
                    with open(story_json) as f:
                        test_story = Story.from_json(f.read())
                    if (test_story.prompt.strip().lower() == prompt.strip().lower()
                            and test_story.age_group == age_group):
                        slug = d
                        story_dir = os.path.join(output_base, slug)
                        story = test_story
                        logger.info("Resuming existing story: %s", slug)
                        break
                except Exception:
                    continue

    if not slug:
        slug = _prompt_to_slug(prompt)
        story_dir = os.path.join(output_base, slug)
        os.makedirs(story_dir, exist_ok=True)

    state = PipelineState.load(slug, story_dir)
    if state and resume:
        logger.info("Resuming pipeline for '%s' from phase %s", slug, state.current_phase)
    elif state is None and story is None:
        state = PipelineState(
            slug=slug,
            prompt=prompt,
            age_group=age_group,
            output_dir=story_dir,
        )
        logger.info("Starting new pipeline for '%s'", slug)

    # ---- Phase 1: Script Generation ----
    if state.phases[Phase.SCRIPT.value].status != "done":
        _print_phase("SCRIPT", "Generating story script")
        state.mark_running(Phase.SCRIPT)
        state.save(story_dir)

        try:
            story = generate_story(
                prompt=prompt,
                age_group=age_group,
                client=client,
                output_dir=output_base,
            )
            # After script gen, story.slug is the canonical slug.
            # If it differs from our initial prompt-derived slug, migrate.
            if story.slug != slug and story_dir != os.path.join(output_base, story.slug):
                old_dir = story_dir
                slug = story.slug
                story_dir = os.path.join(output_base, slug)
                if os.path.exists(old_dir) and not os.path.exists(story_dir):
                    os.rename(old_dir, story_dir)
                state.slug = slug
                state.output_dir = story_dir
            state.mark_done(Phase.SCRIPT)
            state.save(story_dir)
            _print_phase("SCRIPT", f"Done - \"{story.title}\" with {len(story.scenes)} scenes")
        except Exception as exc:
            state.mark_failed(Phase.SCRIPT, str(exc))
            state.save(story_dir)
            _print_phase("SCRIPT", f"FAILED: {exc}")
            raise
    else:
        story_json_path = os.path.join(story_dir, f"{slug}_story.json")
        if os.path.exists(story_json_path):
            with open(story_json_path) as f:
                story = Story.from_json(f.read())

    # ---- Phase 2: Character Reference Images ----
    if state.phases[Phase.CHARACTER_REFS.value].status != "done":
        _print_phase("IMAGES", "Generating character reference images")
        state.mark_running(Phase.CHARACTER_REFS)
        state.save(story_dir)

        try:
            if story is None:
                story_path = os.path.join(story_dir, f"{slug}_story.json")
                with open(story_path) as f:
                    story = Story.from_json(f.read())
            generate_references(story=story, client=client)
            state.mark_done(Phase.CHARACTER_REFS)
            state.save(story_dir)
            _print_phase("IMAGES", "Reference images done")
        except Exception as exc:
            state.mark_failed(Phase.CHARACTER_REFS, str(exc))
            state.save(story_dir)
            _print_phase("IMAGES", f"FAILED: {exc}")
            raise
    else:
        _print_phase("IMAGES", "Already complete, skipping")

    # ---- Phase 3: Scene Images ----
    if state.phases[Phase.SCENE_IMAGES.value].status != "done":
        _print_phase("SCENES", "Generating scene illustrations")
        state.mark_running(Phase.SCENE_IMAGES)
        state.save(story_dir)

        try:
            if story is None:
                story_path = os.path.join(story_dir, f"{slug}_story.json")
                with open(story_path) as f:
                    story = Story.from_json(f.read())
            generate_scene_images(story=story, client=client)
            state.mark_done(Phase.SCENE_IMAGES)
            state.save(story_dir)
            _print_phase("SCENES", "Scene images done")
        except Exception as exc:
            state.mark_failed(Phase.SCENE_IMAGES, str(exc))
            state.save(story_dir)
            _print_phase("SCENES", f"FAILED: {exc}")
            raise
    else:
        _print_phase("SCENES", "Already complete, skipping")

    # ---- Phase 4: Narration ----
    if state.phases[Phase.NARRATION.value].status != "done":
        _print_phase("NARRATION", "Generating voice narration")
        state.mark_running(Phase.NARRATION)
        state.save(story_dir)

        try:
            if story is None:
                story_path = os.path.join(story_dir, f"{slug}_story.json")
                with open(story_path) as f:
                    story = Story.from_json(f.read())
            generate_narration_with_voice(story=story, voice_id=voice)
            state.mark_done(Phase.NARRATION)
            state.save(story_dir)
            _print_phase("NARRATION", "Narration done")
        except Exception as exc:
            state.mark_failed(Phase.NARRATION, str(exc))
            state.save(story_dir)
            _print_phase("NARRATION", f"FAILED: {exc}")
            raise
    else:
        _print_phase("NARRATION", "Already complete, skipping")

    # ---- Phase 5: Video (placeholder) ----
    if state.phases[Phase.VIDEO.value].status != "done":
        _print_phase("VIDEO", "Skipping (Sprint 2)")
        state.mark_done(Phase.VIDEO)
        state.save(story_dir)

    # ---- Phase 6: Export ----
    if state.phases[Phase.EXPORT.value].status != "done":
        _print_phase("EXPORT", "Building storybook exports (HTML, PDF, EPUB)")
        state.mark_running(Phase.EXPORT)
        state.save(story_dir)

        try:
            if story is None:
                story_path = os.path.join(story_dir, f"{slug}_story.json")
                with open(story_path) as f:
                    story = Story.from_json(f.read())

            images_registry = ImageRegistry.load(story_dir, slug)
            html_path = export_html(story=story, images_registry=images_registry)

            # Also generate PDF and EPUB exports
            from export_pipeline.export_manager import export_all
            export_all(story=story, images_registry=images_registry, output_dir=story_dir)

            state.mark_done(Phase.EXPORT)
            state.save(story_dir)
            _print_phase("EXPORT", f"Done -> {html_path}")
        except Exception as exc:
            state.mark_failed(Phase.EXPORT, str(exc))
            state.save(story_dir)
            _print_phase("EXPORT", f"FAILED: {exc}")
            raise
    else:
        _print_phase("EXPORT", "Already complete, skipping")

    _print_phase("DONE", "Pipeline complete!")
    return os.path.join(story_dir, f"{slug}.html")


def _print_phase(phase: str, message: str) -> None:
    print(f"\n[{phase}] {message}")
    logger.info("[%s] %s", phase, message)


def _prompt_to_slug(prompt: str) -> str:
    slug = prompt.lower().strip()[:50]
    slug = "".join(c if c.isalnum() or c in " -_" else "" for c in slug)
    slug = slug.replace(" ", "-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def main():
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: python -m imaginate \"<story prompt>\" [--age kids|adult]")
        print("       python -m imaginate --story <slug>")
        sys.exit(1)

    prompt = sys.argv[1]
    age_group = "kids"
    if "--age" in sys.argv:
        idx = sys.argv.index("--age")
        if idx + 1 < len(sys.argv):
            age_group = sys.argv[idx + 1]

    html_path = run_pipeline(prompt=prompt, age_group=age_group)
    print(f"\nStorybook ready: {html_path}")


if __name__ == "__main__":
    main()
