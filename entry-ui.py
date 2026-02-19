# =============================================================================
# NisWave Music Player UI
# A music player interface built with Pygame featuring folder navigation,
# track selection, and album cover display
# =============================================================================

import pygame
import os
import threading
from pynput.keyboard import Key, Listener
from screeninfo import get_monitors
import sys
from platformdirs import user_music_dir
from pathlib import Path
import random
from get_files import get_music_files_and_directories
from update_image import get_cover_art
from wave_renderer import WaveVisualizer 
from queue_handler import shuffler
from queue_handler import generated_unshuffled_queue

# =============================================================================
# Screen Initialization
# =============================================================================

# Get monitor information and extract screen dimensions
monitors = str(get_monitors())
temp = monitors.split("[Monitor(x=0, y=0, width=")
temp = temp[1].split("height=")
temp = temp[0] + temp[1]
temp = temp.split(", width_mm=")
temp = temp[0]
temp = temp.split(", ")

# Set up media inputs
global media_input
media_input = ""
data_lock = threading.Lock()

def on_press(key):
    global media_input
    with data_lock:
        media_input = key
    

def on_release(key):
    global media_input
    with data_lock:
        media_input = ""

def listening():
    # Start the listener
    # The listener runs in a separate thread, use .join() to prevent the script from exiting immediately
    with Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

threading.Thread(target=listening).start()

# Initialize Pygame and font
pygame.init()
pygame.mixer.init()  # Initialize mixer for audio playback
pygame.font.init()
font = pygame.font.SysFont('Arial', 30)

# Extract and store screen dimensions
default_screen_size = []
for i in range(0, len(temp)):
    default_screen_size.append(int(temp[i]))

default_width, default_height = default_screen_size

# Get initial music directory path
folder_path = Path(user_music_dir())
currently_playing_folder_path = folder_path

# Set up the display window
SCREEN_WIDTH = default_width
SCREEN_HEIGHT = default_height
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("pregus101's NisWave app")

# =============================================================================
# Application State Variables
# =============================================================================

OLD_SIZE = 640  # Previous album cover size (for resize detection)
STARTED = False  # Track whether playback has begun
PLAYING_SONG = ""  # Currently playing song filename

current_time_ms = 0
current_time_sec = current_time_ms / 1000.0

retry = False

# Wave visualizer state
visualizer = None  # Will hold the WaveVisualizer instance
visualizer_running = False

# Create surface objects for directory and file windows
directory_buttons_window = pygame.Surface((SCREEN_WIDTH/5, SCREEN_HEIGHT/2))
file_buttons_window = pygame.Surface((SCREEN_WIDTH/5, SCREEN_HEIGHT/2))

# Set inital button states
play_pause = "play"  # Can be "play" or "pause"
shuffle = False  # Shuffle mode state

# Initialize the played songs
played_songs = []

# Scroll state variables
dir_scroll_offset = 0  # Vertical offset for directories
file_scroll_offset = 0  # Vertical offset for files

# Default cover art path (used if no cover art is found in the MP3 file)
cover_art_path = os.path.join(os.path.dirname(__file__), "assets/default_cover.jpg")  # Default cover art path

# set defualt button colors
skip_button_color = (64, 64, 64)  # Default gray for skip button
play_pause_button_color = (64, 64, 64)  # Default gray for play/pause button
back_button_color = (64, 64, 64)  # Default gray for back button
shuffle_button_color = (64, 64, 64)  # Default gray for shuffle button
previous_button_color = (64, 64, 64)  # Default gray for previous button


old_input = ""

# # Create the queue for auto-playing songs (will be populated with files from the current directory)
# DIRECTORY_ONLY, FILES_ONLY, directory_buttons, file_buttons = get_music_files_and_directories(folder_path, SCREEN_HEIGHT)
# queue = FILES_ONLY.copy()  # Initialize queue with available songs in the current directory

# ============================================================================
# MAIN APPLICATION LOOP
# ============================================================================
while True:
    # Calculate album cover size based on screen resolution for scaling
    SIZE = int(640 * ((SCREEN_WIDTH/1920 + SCREEN_HEIGHT/1147) / 2))
    mouse_pos = pygame.mouse.get_pos()
    
    # ========================================================================
    # EVENT HANDLING
    # ========================================================================
    for event in pygame.event.get():
        # Exit application when window is closed
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEMOTION:
            mouse_pos = event.pos  # Update mouse position on movement

            if shuffle:
                shuffle_button_color = (64, 128, 64) if (SCREEN_WIDTH-SCREEN_WIDTH/5)/2-135+SCREEN_WIDTH/5 <= mouse_pos[0] <= (SCREEN_WIDTH-SCREEN_WIDTH/5)/2-85+SCREEN_WIDTH/5 and SCREEN_HEIGHT-50 <= mouse_pos[1] <= SCREEN_HEIGHT-30 else (32, 64, 32)  # Change shuffle button color on hover
            else:
                shuffle_button_color = (128, 128, 128) if (SCREEN_WIDTH-SCREEN_WIDTH/5)/2-135+SCREEN_WIDTH/5 <= mouse_pos[0] <= (SCREEN_WIDTH-SCREEN_WIDTH/5)/2-85+SCREEN_WIDTH/5 and SCREEN_HEIGHT-50 <= mouse_pos[1] <= SCREEN_HEIGHT-30 else (64, 64, 64)  # Change shuffle button color on hover


            # change play/pause button color on hover
            if (SCREEN_WIDTH-SCREEN_WIDTH/5)/2-25+SCREEN_WIDTH/5 <= mouse_pos[0] <= (SCREEN_WIDTH-SCREEN_WIDTH/5)/2+25+SCREEN_WIDTH/5 and SCREEN_HEIGHT-50 <= mouse_pos[1] <= SCREEN_HEIGHT-30:
                play_pause_button_color = (128, 128, 128)  # Lighter gray on hover
            else:        
                play_pause_button_color = (64, 64, 64)  # Default gray 

            # Change back button color on hover
            if SCREEN_WIDTH/5-40 <= mouse_pos[0] <= SCREEN_WIDTH/5-20 and 5 <= mouse_pos[1] <= 25:
                back_button_color = (128, 128, 128)  # Lighter gray on hover
            else:
                back_button_color = (64, 64, 64)  # Default gray

            # Change skip button color on hover
            if (SCREEN_WIDTH-SCREEN_WIDTH/5)/2+30+SCREEN_WIDTH/5 <= mouse_pos[0] <= (SCREEN_WIDTH-SCREEN_WIDTH/5)/2+80+SCREEN_WIDTH/5 and SCREEN_HEIGHT-50 <= mouse_pos[1] <= SCREEN_HEIGHT-30:
                skip_button_color = (128, 128, 128)  # Lighter gray on hover
            else:
                skip_button_color = (64, 64, 64)  # Default gray

            # prevoius button color on hover
            if (SCREEN_WIDTH-SCREEN_WIDTH/5)/2-80+SCREEN_WIDTH/5 <= mouse_pos[0] <= (SCREEN_WIDTH-SCREEN_WIDTH/5)/2-30+SCREEN_WIDTH/5 and SCREEN_HEIGHT-50 <= mouse_pos[1] <= SCREEN_HEIGHT-30:
                previous_button_color = (128, 128, 128)  # Lighter gray on hover
            else:
                previous_button_color = (64, 64, 64)  # Default gray


        # Handle mouse button clicks (folder/file selection and navigation)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button only
                # Get current directory contents for button interaction
                
                DIRECTORY_ONLY, FILES_ONLY, directory_buttons, file_buttons = get_music_files_and_directories(folder_path, SCREEN_HEIGHT, dir_scroll_offset, file_scroll_offset)

                # Debug output (can be removed later)
                print(SCREEN_WIDTH/5-25 <= mouse_pos[0] <= SCREEN_WIDTH/5-5 and 5 <= mouse_pos[1] <= 25)
                print(SCREEN_WIDTH/5-25, mouse_pos[0], SCREEN_WIDTH/5-5, mouse_pos[1])

                # Check if back button was clicked (navigate to parent directory)
                if SCREEN_WIDTH/5-40 <= mouse_pos[0] <= SCREEN_WIDTH/5-20 and 5 <= mouse_pos[1] <= 25:
                    folder_path = os.path.dirname(folder_path)
                    print("Back button clicked, new folder path:", folder_path)

                # Check if skip button was clicked
                if (SCREEN_WIDTH-SCREEN_WIDTH/5)/2+30+SCREEN_WIDTH/5 <= mouse_pos[0] <= (SCREEN_WIDTH-SCREEN_WIDTH/5)/2+80+SCREEN_WIDTH/5 and SCREEN_HEIGHT-50 <= mouse_pos[1] <= SCREEN_HEIGHT-30 and STARTED:
                    pygame.mixer.music.stop()

                # Check if previous button was clicked
                if (SCREEN_WIDTH-SCREEN_WIDTH/5)/2-80+SCREEN_WIDTH/5 <= mouse_pos[0] <= (SCREEN_WIDTH-SCREEN_WIDTH/5)/2-30+SCREEN_WIDTH/5 and SCREEN_HEIGHT-50 <= mouse_pos[1] <= SCREEN_HEIGHT-30 and STARTED:
                    
                    if current_time_sec <= 10:
                        try:
                            file_path = os.path.join(currently_playing_folder_path, played_songs[-1])
                            skip = False
                        except:
                            skip = True

                            print(skip)
                        
                        if not skip:
                            STARTED = True
                            PLAYING_SONG = os.path.basename(file_path)

                            played_songs.remove(PLAYING_SONG)
                            queue_raw.insert(0, PLAYING_SONG)  # Add current song back to the front of the queue_raw
                            queue.insert(0, PLAYING_SONG)
                                
                            # Get album cover art for the selected track
                            render_size, cover_art_path = get_cover_art(file_path, SIZE)

                            # CREATE AND START WAVE VISUALIZER
                            visualizer = WaveVisualizer(file_path, 
                                                        render_size[0], 
                                                        render_size[1])
                            # Set wave color to contrast with album cover
                            cover_art_path = os.path.join(os.path.dirname(__file__), "temp_cover_art/temp_cover.png")
                            visualizer.set_color_from_image(cover_art_path)
                            visualizer.load_audio()
                            visualizer.play()
                            visualizer_running = True

                    else:
                        # CREATE AND START WAVE VISUALIZER
                        visualizer = WaveVisualizer(file_path, 
                                                    render_size[0], 
                                                    render_size[1])
                        visualizer.load_audio()
                        visualizer.play()
                        visualizer_running = True

                # Check if pause/play button was clicked
                if (SCREEN_WIDTH-SCREEN_WIDTH/5)/2-25+SCREEN_WIDTH/5 <= mouse_pos[0] <= (SCREEN_WIDTH-SCREEN_WIDTH/5)/2+25+SCREEN_WIDTH/5 and SCREEN_HEIGHT-75 <= mouse_pos[1] <= SCREEN_HEIGHT-25:
                    if play_pause == "play" and STARTED:
                        STARTED = False
                        play_pause = "pause"
                        try:
                            WaveVisualizer.set_pause_state(visualizer, True)  # Pause the visualizer
                        except:
                            pass  # Visualizer may not be initialized yet, ignore if error occurs
                    else:
                        STARTED = True
                        play_pause = "play"
                        try:
                            WaveVisualizer.set_pause_state(visualizer, False)  # Unpause the visualizer
                        except:
                            pass  # Visualizer may not be initialized yet, ignore if error occurs
                            STARTED = False
                            

                # Check if shuffle button was clicked
                if (SCREEN_WIDTH-SCREEN_WIDTH/5)/2-135+SCREEN_WIDTH/5 <= mouse_pos[0] <= (SCREEN_WIDTH-SCREEN_WIDTH/5)/2-85+SCREEN_WIDTH/5 and SCREEN_HEIGHT-50 <= mouse_pos[1] <= SCREEN_HEIGHT-30:
                    if not PLAYING_SONG == '':
                        if shuffle:
                            queue = generated_unshuffled_queue(PLAYING_SONG, queue_raw)
                        else:
                            queue = shuffler(queue_raw, PLAYING_SONG)
                            print(queue)

                    shuffle = not shuffle  # Toggle shuffle state

                # Check if a directory was clicked and navigate into it
                for button in directory_buttons:
                    if button[0] <= mouse_pos[1] <= button[0] + 30 and mouse_pos[1] <= SCREEN_HEIGHT/2 and mouse_pos[0] <= song_select_window:
                        folder_path = os.path.join(folder_path, button[1])
        
                # Check if a music file was clicked to play it
                for button in file_buttons:
                    if button[0] <= mouse_pos[1] <= button[0] + 30 and mouse_pos[0] <= song_select_window:
                        # refresh variables for new song
                        queue_raw = generated_unshuffled_queue(button[1], FILES_ONLY.copy())

                        if shuffle:
                            queue = shuffler(queue_raw, button[1], True)
                        else:
                            queue = queue_raw.copy()
                        
                        play_pause = "play"  # Reset play/pause state to "play" when a new song is selected
                        played_songs = []  # Clear the list of played songs when a new song is selected
                        
                        # Load and play the selected file
                        file_path = os.path.join(folder_path, button[1])
                        currently_playing_folder_path = folder_path  # Update the currently playing folder path
                        STARTED = True
                        # queue_raw.remove(button[1])
                        # queue.remove(button[1])
                        PLAYING_SONG = button[1]

                        # Get album cover art for the selected track
                        render_size, cover_art_path = get_cover_art(file_path, SIZE)

                        # CREATE AND START WAVE VISUALIZER
                        visualizer = WaveVisualizer(file_path, 
                                                   render_size[0], 
                                                   render_size[1])
                        # Set wave color to contrast with album cover
                        visualizer.set_color_from_image(cover_art_path)
                        visualizer.load_audio()
                        visualizer.play()
                        visualizer_running = True

        if event.type == pygame.MOUSEWHEEL:
            if mouse_pos[0] <= song_select_window:
                if mouse_pos[1] < SCREEN_HEIGHT/2:  # Directory section
                    dir_scroll_offset -= event.y * 40  # Scroll by item height
                    dir_scroll_offset = max(0, min(dir_scroll_offset, 
                                                   max(0, len(DIRECTORY_ONLY) * 40 - (SCREEN_HEIGHT/2 - 60))))
                else:  # File section
                    file_scroll_offset -= event.y * 40
                    file_scroll_offset = max(0, min(file_scroll_offset,
                                                    max(0, len(FILES_ONLY) * 40 - (SCREEN_HEIGHT/2 - 60))))

        
        # Handle spacebar for pause/play
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and visualizer:
                if play_pause == "play" and STARTED:
                    pygame.mixer.music.pause()
                    STARTED = False
                    play_pause = "pause"
                    try:
                        WaveVisualizer.set_pause_state(visualizer, True)  # Pause the visualizer
                    except:
                        pass  # Visualizer may not be initialized yet, ignore if error occurs
                else:
                    pygame.mixer.music.unpause()
                    STARTED = True
                    play_pause = "play"
                    try:
                        WaveVisualizer.set_pause_state(visualizer, False)  # Unpause the visualizer
                    except:
                        pass  # Visualizer may not be initialized yet, ignore if error occurs
                        STARTED = False

    with data_lock:
        if not old_input == media_input:
            old_input = media_input
            if media_input == Key.media_play_pause and visualizer:
                    if play_pause == "play" and STARTED:
                        pygame.mixer.music.pause()
                        STARTED = False
                        play_pause = "pause"
                        try:
                            WaveVisualizer.set_pause_state(visualizer, True)  # Pause the visualizer
                        except:
                            pass  # Visualizer may not be initialized yet, ignore if error occurs
                    else:
                        pygame.mixer.music.unpause()
                        STARTED = True
                        play_pause = "play"
                        try:
                            WaveVisualizer.set_pause_state(visualizer, False)  # Unpause the visualizer
                        except:
                            pass  # Visualizer may not be initialized yet, ignore if error occurs
                            STARTED = False


        

    # ========================================================================
    # AUTO-PLAY & QUEUE MANAGEMENT
    # ========================================================================
    
    # Auto-play next song when current song finishes
    if STARTED and not len(queue_raw) <= 0:
        if not pygame.mixer.music.get_busy():

            try:
                queue_raw.remove(PLAYING_SONG)
                queue.remove(PLAYING_SONG)
            except:
                retry = True

            newsong = queue[0] if queue else ""

            file_path = os.path.join(currently_playing_folder_path, newsong)
            if os.path.isfile(file_path):

                played_songs.append(PLAYING_SONG)  # Add the previous song to the list of played songs
                PLAYING_SONG = newsong

                # queue_raw.remove(newsong)
                # queue.remove(newsong)

                # Get cover art and update visualizer for the new song
                render_size, cover_art_path = get_cover_art(file_path, SIZE)
                
                # UPDATE VISUALIZER FOR NEW SONG
                visualizer = WaveVisualizer(file_path, 
                                        render_size[0], 
                                        render_size[1])
                # Set wave color to contrast with album cover
                visualizer.set_color_from_image(cover_art_path)
                visualizer.load_audio()
                visualizer.play()
                visualizer_running = True
            else:
                print("No more songs in the queue to play.")
                STARTED = False  # Stop playback if there are no more songs to play
                visualizer_running = False  # Stop the visualizer as well
                cover_art_path = os.path.join(os.path.dirname(__file__), "assets/default_cover.jpg")  # Reset to default cover art path
            
            if retry:
                pygame.mixer.music.stop()
                retry = False

    # ========================================================================
    # RENDERING & DISPLAY
    # ========================================================================
    # ========================================================================
    # RENDERING & DISPLAY
    # ========================================================================

    current_time_ms = pygame.mixer.music.get_pos()
    current_time_sec = current_time_ms / 1000.0
    
    # Update screen dimensions in case window was resized
    SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()
    song_select_window = SCREEN_WIDTH / 5
    
    # ---- LEFT SIDEBAR: Directory and File Selection ----
    
    # Draw left sidebar background (light gray for directory/file selection area)
    pygame.draw.rect(screen, (40, 40, 40), (0, 0, song_select_window, SCREEN_HEIGHT))

    # Get directories and files in current folder
    DIRECTORY_ONLY, FILES_ONLY, directory_buttons, file_buttons = get_music_files_and_directories(folder_path, SCREEN_HEIGHT, dir_scroll_offset, file_scroll_offset)

    # Create subsurface for folder section (top half of sidebar)
    folder_surf = screen.subsurface(0, 0, song_select_window, SCREEN_HEIGHT)
    
    # Create subsurface for file list section (bottom half of sidebar)
    file_surf = screen.subsurface(0, SCREEN_HEIGHT/2, song_select_window, SCREEN_HEIGHT/2)

    # Draw folder list with header
    for directory in DIRECTORY_ONLY:
        text_surface = font.render(directory, True, (255, 255, 255))
        folder_surf.blit(text_surface, (10, (DIRECTORY_ONLY.index(directory)+1)*40 + 10 - dir_scroll_offset))

    pygame.draw.rect(screen, (40, 40, 40), (0, 0, song_select_window, 40))
    text_surface = font.render("Folders:", True, (255, 255, 255))
    folder_surf.blit(text_surface, (10, 10))

    # Draw file list background
    pygame.draw.rect(screen, (40, 40, 40), (0, SCREEN_HEIGHT/2, song_select_window, SCREEN_HEIGHT/2))

    # Draw file list with header
    for file in FILES_ONLY:
        text_surface = font.render(file, True, (255, 255, 255))
        file_surf.blit(text_surface, (10, (FILES_ONLY.index(file)+1)*40 + 10 - file_scroll_offset))

    pygame.draw.rect(screen, (40, 40, 40), (0, SCREEN_HEIGHT/2, song_select_window, 40))   
    text_surface = font.render("Files:", True, (255, 255, 255))
    file_surf.blit(text_surface, (10, 10))

    try:
        # Draw scrollbars
        dir_max_scroll = max(0, len(DIRECTORY_ONLY) * 40 - (SCREEN_HEIGHT/2 - 60))
        if dir_max_scroll > 0:
            scrollbar_h = (SCREEN_HEIGHT/2 - 60) * (SCREEN_HEIGHT/2 - 60) / (len(DIRECTORY_ONLY) * 40)
            scrollbar_y = dir_scroll_offset * (SCREEN_HEIGHT/2 - 60) / (len(DIRECTORY_ONLY) * 40)
            pygame.draw.rect(screen, (100, 100, 100), 
                            (song_select_window - 10, scrollbar_y, 8, scrollbar_h))

        file_max_scroll = max(0, len(FILES_ONLY) * 40 - (SCREEN_HEIGHT/2 - 60))
        if file_max_scroll > 0:
            scrollbar_h = (SCREEN_HEIGHT/2 - 60) * (SCREEN_HEIGHT/2 - 60) / (len(FILES_ONLY) * 40)
            scrollbar_y = file_scroll_offset * (SCREEN_HEIGHT/2 - 60) / (len(FILES_ONLY) * 40)
            pygame.draw.rect(screen, (100, 100, 100), 
                            (song_select_window - 10, SCREEN_HEIGHT/2 + scrollbar_y, 8, scrollbar_h))
    except:
        print("Not enough space to draw scrollbars")

    # ---- RIGHT SIDE: Album Cover and Visualizer ----
    
    # Draw right side background (dark gray for album cover area)
    pygame.draw.rect(screen, (20, 20, 20), (song_select_window, 0, SCREEN_WIDTH - song_select_window, SCREEN_HEIGHT))
    
    # Draw back button (small gray square)
    pygame.draw.rect(screen, back_button_color, (SCREEN_WIDTH/5-40, 5, 20, 20))

    #draw media control buttons (small gray rectangles)
    # pygame.draw.rect(screen, play_pause_button_color, ((SCREEN_WIDTH-SCREEN_WIDTH/5)/2-25+SCREEN_WIDTH/5, SCREEN_HEIGHT-30, 50, 20))
    if play_pause == "pause":
        play_button = pygame.image.load(os.path.join(os.path.dirname(__file__), "assets/Play_play.jpg"))
    else:
        play_button = pygame.image.load(os.path.join(os.path.dirname(__file__), "assets/Play_pause.jpg"))

    play_button_rect = play_button.get_rect()
    play_button_rect.center = ((SCREEN_WIDTH-SCREEN_WIDTH/5)/2+SCREEN_WIDTH/5, SCREEN_HEIGHT-50)
    screen.blit(play_button, play_button_rect)
        

    pygame.draw.rect(screen, skip_button_color, ((SCREEN_WIDTH-SCREEN_WIDTH/5)/2+30+SCREEN_WIDTH/5, SCREEN_HEIGHT-50, 50, 20))
    pygame.draw.rect(screen, previous_button_color, ((SCREEN_WIDTH-SCREEN_WIDTH/5)/2-80+SCREEN_WIDTH/5, SCREEN_HEIGHT-50, 50, 20))
    pygame.draw.rect(screen, shuffle_button_color, ((SCREEN_WIDTH-SCREEN_WIDTH/5)/2-135+SCREEN_WIDTH/5, SCREEN_HEIGHT-50, 50, 20))

    # Load and display album cover art, centered on right side
    album_cover = pygame.image.load(cover_art_path)

    image_rect = album_cover.get_rect()
    # Center the cover image on the right side of the screen
    image_rect.center = ((SCREEN_WIDTH-(SCREEN_WIDTH/5))/2+SCREEN_WIDTH/5, SCREEN_HEIGHT/2)
    screen.blit(album_cover, image_rect)

    # ---- NOW PLAYING INFO ----
    
    # Display currently playing song name
    if STARTED:
        text_surface = font.render("Now Playing: " + PLAYING_SONG, True, (255, 255, 255))
        screen.blit(text_surface, ((SCREEN_WIDTH-song_select_window)/2+SCREEN_WIDTH/5-(13+len(PLAYING_SONG))*7, SCREEN_HEIGHT/2 + render_size[1]/2 + 10))

    # Update album cover if screen size changed
    if SIZE != OLD_SIZE:
        render_size, cover_art_path = get_cover_art(os.path.join(currently_playing_folder_path, PLAYING_SONG), SIZE)

    OLD_SIZE = SIZE
    
    # ---- WAVE VISUALIZATION RENDERING ----
    
    try:
        # Render wave visualization on the right side
        if visualizer and visualizer_running:
            # Create a subsurface for the visualizer (right side of screen)
            vis_surface = screen.subsurface(song_select_window+(((SCREEN_WIDTH-song_select_window)/2-render_size[0]/2)), 0,
                                        render_size[0], SCREEN_HEIGHT/2+render_size[1]/2)
            
            # Render one frame of the wave visualization
            if not visualizer.render_frame(vis_surface, mouse_pos):
                visualizer_running = False  # Song finished, stop rendering
            
            # Update visualizer render position if window was resized
            if visualizer:
                visualizer.update_render_size(int(render_size[0]), 
                                            int((SCREEN_HEIGHT/2)+(render_size[1]/2)))
    except:
        pass # give the visualizer some time to initialize before trying to create the subsurface for it, ignore errors if it fails at first

    # ---- UPDATE DISPLAY ----
    
    # Refresh the display with all rendered elements
    pygame.display.flip()