import os
import asyncio
from datetime import datetime
import streamlit as st
import edge_tts
from groq import Groq
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips

# Page Configuration
st.set_page_config(
    page_title="AI Kids Animation Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Clean Professional Look
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .scene-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .card-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

API_KEY = "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"
client = Groq(api_key=API_KEY)
VOICE = "en-US-AnaNeural"

# Session State Initialization
if "project_dir" not in st.session_state:
    st.session_state.project_dir = None
if "scenes_data" not in st.session_state:
    st.session_state.scenes_data = []

async def generate_speech(text, file_path):
    communicator = edge_tts.Communicate(text, VOICE)
    await communicator.save(file_path)

# Header
st.title("🎬 AI Kids Cartoon Studio")
st.markdown("Automate story creation, character voiceovers, and video assembly in minutes.")
st.divider()

# --- Sidebar: Story Setup ---
with st.sidebar:
    st.header("1. Story Generation")
    story_topic = st.text_input(
        "Story Idea / Topic:",
        placeholder="e.g., A little squirrel finding a golden acorn"
    )
    
    generate_btn = st.button("✨ Generate Story & Audio", use_container_width=True, type="primary")

    if generate_btn:
        if not story_topic.strip():
            st.error("Please enter a story topic first.")
        else:
            with st.spinner("Crafting story scenes and synthesizing audio..."):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                project_dir = os.path.join("projects", f"story_{timestamp}")
                audio_dir = os.path.join(project_dir, "audio")
                scenes_dir = os.path.join(project_dir, "scenes")
                os.makedirs(audio_dir, exist_ok=True)
                os.makedirs(scenes_dir, exist_ok=True)

                prompt = f"""
You are an expert kids cartoon director. Create a 4-scene kids story about: "{story_topic}".
Each scene represents exactly 8 seconds of action.

CRITICAL INSTRUCTIONS:
- You MUST separate each scene using the exact delimiter: ---SPLIT---
- Do NOT add markdown formatting inside the fields.
- Strictly follow this format:

[SCENE 1]
PROMPT: A detailed 3D Pixar Disney style prompt describing the visuals, camera movement, and characters for an 8-second video clip.
VOICEOVER: The narrator line for this scene.
---SPLIT---
[SCENE 2]
PROMPT: ...
VOICEOVER: ...
---SPLIT---
[SCENE 3]
PROMPT: ...
VOICEOVER: ...
---SPLIT---
[SCENE 4]
PROMPT: ...
VOICEOVER: ...
"""
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="openai/gpt-oss-120b",
                )
                
                raw_text = response.choices[0].message.content
                raw_blocks = raw_text.split("---SPLIT---")
                
                scenes_info = []
                idx = 0
                for block in raw_blocks:
                    block = block.strip()
                    if "PROMPT:" in block and "VOICEOVER:" in block:
                        idx += 1
                        parts = block.split("VOICEOVER:")
                        p_text = parts[0].replace(f"[SCENE {idx}]", "").replace("PROMPT:", "").strip()
                        v_text = parts[1].strip().split("\n")[0].replace('"', '')
                        
                        audio_path = os.path.join(audio_dir, f"scene_{idx}.mp3")
                        asyncio.run(generate_speech(v_text, audio_path))
                        
                        scenes_info.append({
                            "index": idx,
                            "prompt": p_text,
                            "voiceover": v_text,
                            "audio_path": audio_path
                        })

                st.session_state.project_dir = project_dir
                st.session_state.scenes_data = scenes_info
                st.success("Story and voiceovers generated successfully!")

# --- Main Workspace ---
if st.session_state.scenes_data:
    st.subheader("2. Video Prompting & File Upload")
    st.info("Copy the prompt for each scene to generate the video, then upload the downloaded clip below.")

    cols = st.columns(4)
    uploaded_files = {}

    for i, sc in enumerate(st.session_state.scenes_data):
        with cols[i]:
            st.markdown(f'<div class="card-title">Scene {sc["index"]}</div>', unsafe_allow_html=True)
            st.text_area("Video Prompt:", sc["prompt"], height=150, key=f"prompt_{i}")
            st.caption(f"**Narration:** {sc['voiceover']}")
            
            if os.path.exists(sc["audio_path"]):
                st.audio(sc["audio_path"])
            
            uploaded_file = st.file_uploader(f"Upload Video {sc['index']}", type=["mp4"], key=f"video_{i}")
            if uploaded_file:
                target_path = os.path.join(st.session_state.project_dir, "scenes", f"scene_{sc['index']}.mp4")
                with open(target_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                uploaded_files[sc['index']] = target_path

    st.divider()
    st.subheader("3. Video Assembly & Export")

    all_ready = len(uploaded_files) == 4
    if not all_ready:
        st.warning(f"Please upload all 4 video scenes to activate the final assembly ({len(uploaded_files)}/4 ready).")

    if st.button("🎬 Assemble & Render Final Video", disabled=not all_ready, use_container_width=True, type="primary"):
        with st.spinner("Synchronizing audio, stitching clips, and balancing soundtrack..."):
            try:
                final_clips = []
                for i in range(1, 5):
                    v_p = uploaded_files[i]
                    a_p = os.path.join(st.session_state.project_dir, "audio", f"scene_{i}.mp3")
                    
                    v_clip = VideoFileClip(v_p)
                    a_clip = AudioFileClip(a_p)
                    
                    duration = max(v_clip.duration, a_clip.duration)
                    if hasattr(v_clip, 'with_duration'):
                        v_clip = v_clip.with_duration(duration).with_audio(a_clip)
                    else:
                        v_clip = v_clip.set_duration(duration).set_audio(a_clip)
                        
                    final_clips.append(v_clip)

                full_video = concatenate_videoclips(final_clips, method="compose")

                # Background Music Integration
                music_candidates = ["music.mp3", os.path.join("music", "music.mp3")]
                music_path = next((m for m in music_candidates if os.path.exists(m)), None)

                if music_path:
                    raw_bg = AudioFileClip(music_path)
                    if hasattr(raw_bg, 'multiply_volume'):
                        bg_music = raw_bg.multiply_volume(0.15)
                    else:
                        bg_music = raw_bg.volumex(0.15)
                        
                    if hasattr(bg_music, 'with_duration'):
                        bg_music = bg_music.with_duration(full_video.duration)
                        full_video = full_video.with_audio(CompositeAudioClip([full_video.audio, bg_music]))
                    else:
                        bg_music = bg_music.set_duration(full_video.duration)
                        full_video = full_video.set_audio(CompositeAudioClip([full_video.audio, bg_music]))

                output_path = os.path.join(st.session_state.project_dir, "final_video.mp4")
                full_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")

                st.success("🎉 Final Video Successfully Rendered!")
                st.video(output_path)
                with open(output_path, "rb") as vf:
                    st.download_button(
                        label="⬇️ Download Cartoon Video",
                        data=vf,
                        file_name="cartoon_story.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"Error during video assembly: {e}")
else:
    st.info("👈 Enter your story concept in the sidebar and click 'Generate Story & Audio' to start.")