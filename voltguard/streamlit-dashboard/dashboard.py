"""
VoltGuard Phase 1D - Streamlit Dashboard (Redesigned)
Real-time visualization of system state, sensor readings, and event log

SAFETY DESIGN:
- Read-only display (no control buttons that bypass hardware safety)
- All state comes from DecisionEngine
- Controlled refresh via st.rerun() with 1-2s interval
- NO persistent background threads (prevents instability)
- All safety enforcement happens at hardware/Python level, not UI
- Fully responsive design (desktop, tablet, mobile)
- Light and dark theme support
"""

import sys
import time
from datetime import datetime
from pathlib import Path
from collections import deque

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Add parent directory for imports
base_dir = Path(__file__).parent.parent
python_engine_dir = base_dir / "python-engine"
sys.path.insert(0, str(base_dir))
sys.path.insert(0, str(python_engine_dir))

from main import VoltGuardApplication


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="VoltGuard Dashboard",
    page_icon=":zap:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

# Theme preference (persists across reruns)
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "dark"  # "dark" or "light"

# Simulator mode state (used to rebuild app when mode changes)
if "simulator_mode" not in st.session_state:
    st.session_state.simulator_mode = "stable"

# Initialize session state (persists across reruns)
if "app" not in st.session_state:
    """Initialize VoltGuard application on first load"""
    st.session_state.app = VoltGuardApplication(
        use_simulator=True,
        simulator_mode=st.session_state.simulator_mode,
        enable_logging=True
    )
    st.session_state.last_update_time = time.time()
    st.session_state.cycle_count = 0

if "last_displayed_events" not in st.session_state:
    """Track displayed events to highlight new ones"""
    st.session_state.last_displayed_events = 0

# Data history for charts (up to 60 points)
if "current_history" not in st.session_state:
    st.session_state.current_history = deque(maxlen=60)

if "temp_history" not in st.session_state:
    st.session_state.temp_history = deque(maxlen=60)

if "state_history" not in st.session_state:
    st.session_state.state_history = deque(maxlen=60)

if "timestamp_history" not in st.session_state:
    st.session_state.timestamp_history = deque(maxlen=60)


# ============================================================================
# THEME & COLOR CONFIGURATION
# ============================================================================

def get_colors():
    """Return color palette based on current theme"""
    if st.session_state.theme_mode == "dark":
        return {
            "bg_primary": "#0d1117",
            "bg_secondary": "#161b22",
            "text_primary": "#c9d1d9",
            "text_secondary": "#8b949e",
            "safe": "#00ff41",
            "warning": "#ffa500",
            "critical": "#ff1744",
            "border": "#30363d",
            "chart_bg": "#161b22",
        }
    else:  # light mode
        return {
            "bg_primary": "#ffffff",
            "bg_secondary": "#f6f8fa",
            "text_primary": "#24292f",
            "text_secondary": "#57606a",
            "safe": "#22c55e",
            "warning": "#f97316",
            "critical": "#ef4444",
            "border": "#d0d7de",
            "chart_bg": "#f6f8fa",
        }


def apply_theme_css():
    """Apply custom CSS for theme"""
    colors = get_colors()
    theme_css = f"""
    <style>
    /* Force color scheme */
    :root {{
        color-scheme: {'dark' if st.session_state.theme_mode == 'dark' else 'light'};
        --bg-primary: {colors['bg_primary']};
        --bg-secondary: {colors['bg_secondary']};
        --text-primary: {colors['text_primary']};
        --text-secondary: {colors['text_secondary']};
        --border: {colors['border']};
    }}
    
    * {{
        color-scheme: {'dark' if st.session_state.theme_mode == 'dark' else 'light'} !important;
    }}
    
    /* Body and main container */
    body {{
        background-color: {colors['bg_primary']} !important;
        color: {colors['text_primary']} !important;
    }}
    
    .main {{
        background-color: {colors['bg_primary']} !important;
    }}
    
    /* Streamlit native elements override */
    .stApp {{
        background-color: {colors['bg_primary']} !important;
    }}
    
    /* Navbar/header styling */
    header {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
    }}
    
    [data-testid="stHeader"] {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
    }}
    
    [data-testid="stHeader"] > div {{
        background-color: {colors['bg_secondary']} !important;
    }}
    
    /* Text colors for all elements */
    h1, h2, h3, h4, h5, h6 {{
        color: {colors['text_primary']} !important;
    }}
    
    p, span, div, label {{
        color: {colors['text_primary']} !important;
    }}
    
    /* Force all inputs to respect theme */
    input, select, textarea {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
        border-color: {colors['border']} !important;
    }}
    
    /* Streamlit select dropdown - React Select component */
    .Select-value, .Select-placeholder {{
        color: {colors['text_primary']} !important;
    }}
    
    .Select-control {{
        background-color: {colors['bg_secondary']} !important;
        border-color: {colors['border']} !important;
    }}
    
    .Select-menu {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
    }}
    
    .Select-option {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
    }}
    
    .Select-option:hover {{
        background-color: {colors['border']} !important;
    }}
    
    .Select-input {{
        color: {colors['text_primary']} !important;
    }}
    
    .Select-arrow-zone {{
        color: {colors['text_primary']} !important;
    }}
    
    /* Override Streamlit's default theme for selectbox */
    [data-testid="stSelectbox"] {{
        color: {colors['text_primary']} !important;
    }}
    
    [data-testid="stSelectbox"] > div > div > div > div {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
    }}
    
    /* Metric cards */
    .stMetric {{
        background-color: {colors['bg_secondary']} !important;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid {colors['border']} !important;
    }}
    
    .stMetric > div > div > div > div {{
        color: {colors['text_primary']} !important;
    }}
    
    .stMetric > div > div > div > div > div {{
        color: {colors['text_secondary']} !important;
    }}
    
    /* State banner */
    .state-banner {{
        background: linear-gradient(135deg, {colors['bg_secondary']} 0%, {colors['bg_secondary']} 100%);
        border: 2px solid {colors['border']};
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
    }}
    
    /* Chart container */
    .chart-container {{
        background-color: {colors['bg_secondary']};
        border: 1px solid {colors['border']};
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }}
    
    /* Event rows */
    .event-row {{
        background-color: {colors['bg_secondary']};
        border-left: 4px solid {colors['border']};
        padding: 12px;
        margin-bottom: 8px;
        border-radius: 4px;
    }}
    
    /* Info cards */
    .info-card {{
        background-color: {colors['bg_secondary']};
        border: 1px solid {colors['border']};
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 12px;
    }}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background-color: {colors['bg_secondary']} !important;
        border-right: 1px solid {colors['border']} !important;
    }}
    
    [data-testid="stSidebar"] > div {{
        background-color: {colors['bg_secondary']} !important;
    }}
    
    .sidebar-header {{
        background: linear-gradient(135deg, {colors['bg_primary']} 0%, {colors['bg_secondary']} 100%);
        border: 1px solid {colors['border']};
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        text-align: center;
    }}
    
    .sidebar-section {{
        background-color: {colors['bg_primary']};
        border: 1px solid {colors['border']};
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 16px;
    }}
    
    .sidebar-section-title {{
        color: {colors['text_primary']} !important;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid {colors['border']};
    }}
    
    /* Status indicator */
    .status-indicator {{
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 2s infinite;
    }}
    
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.5; }}
    }}
    
    /* Navigation items */
    .nav-item {{
        padding: 10px 12px;
        border-radius: 8px;
        margin-bottom: 4px;
        transition: all 0.2s ease;
        cursor: pointer;
    }}
    
    .nav-item:hover {{
        background-color: {colors['border']};
    }}
    
    /* Radio button styling */
    [data-testid="stRadio"] > div > div > div > label {{
        color: {colors['text_primary']} !important;
    }}
    
    [data-testid="stRadio"] > div > div > div > label > div {{
        background-color: {colors['bg_secondary']} !important;
        border: 1px solid {colors['border']} !important;
    }}
    
    /* Button styling */
    button {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
        border: 1px solid {colors['border']} !important;
    }}
    
    .stButton > button {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
        border: 1px solid {colors['border']} !important;
    }}
    
    .stButton > button:hover {{
        background-color: {colors['border']} !important;
    }}
    
    .stButton > button:focus {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
    }}
    
    [data-testid="stBaseButton-primary"] {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
        border: 1px solid {colors['border']} !important;
    }}
    
    [data-testid="stBaseButton-primary"] > button {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
        border: 1px solid {colors['border']} !important;
    }}
    
    /* Selectbox styling - more comprehensive */
    [data-testid="stSelectbox"] {{
        background-color: {colors['bg_secondary']} !important;
    }}
    
    [data-testid="stSelectbox"] * {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
    }}
    
    [data-testid="stSelectbox"] > div {{
        background-color: {colors['bg_secondary']} !important;
    }}
    
    [data-testid="stSelectbox"] > div > div {{
        background-color: {colors['bg_secondary']} !important;
    }}
    
    [data-testid="stSelectbox"] > div > div > div {{
        background-color: {colors['bg_secondary']} !important;
    }}
    
    [data-testid="stSelectbox"] > div > div > div > div {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
    }}
    
    [data-testid="stSelectbox"] > div > div > div > div > div {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
    }}
    
    [data-testid="stSelectbox"] > div > div > div > div > div > div {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
    }}
    
    [data-testid="stSelectbox"] select {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
        border: 1px solid {colors['border']} !important;
    }}
    
    [data-testid="stSelectbox"] option {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
    }}
    
    /* All select elements */
    select {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
        border: 1px solid {colors['border']} !important;
    }}
    
    option {{
        background-color: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
    }}
    
    /* Tooltip styling */
    .stTooltip {{
        background-color: {colors['bg_primary']} !important;
        color: {colors['text_primary']} !important;
        border: 1px solid {colors['border']} !important;
    }}
    
    /* Streamlit help tooltip */
    [data-testid="stTooltip"] {{
        background-color: {colors['bg_primary']} !important;
        color: {colors['text_primary']} !important;
        border: 1px solid {colors['border']} !important;
    }}
    
    /* Caption styling */
    .stCaption {{
        color: {colors['text_secondary']} !important;
    }}
    
    /* Divider styling */
    hr {{
        border-color: {colors['border']} !important;
    }}
    
    /* Dataframe styling */
    .stDataFrame {{
        background-color: {colors['bg_secondary']} !important;
    }}
    
    .stDataFrame > div {{
        background-color: {colors['bg_secondary']} !important;
    }}
    
    /* Chart styling */
    .stPlotlyChart {{
        background-color: {colors['chart_bg']} !important;
    }}
    
    .stPlotlyChart > div {{
        background-color: {colors['chart_bg']} !important;
    }}
    
    /* Line chart specific */
    .stLineChart {{
        background-color: {colors['chart_bg']} !important;
    }}
    
    .stLineChart > div {{
        background-color: {colors['chart_bg']} !important;
    }}
    
    /* Info, success, warning, error boxes */
    .stAlert {{
        background-color: {colors['bg_secondary']} !important;
        border: 1px solid {colors['border']} !important;
    }}
    
    /* Responsive adjustments for mobile */
    @media (max-width: 768px) {{
        .stMetric {{
            padding: 10px;
            margin-bottom: 12px;
        }}
        
        .state-banner {{
            padding: 15px;
            margin-bottom: 15px;
        }}
        
        .stColumn {{
            margin-bottom: 16px;
        }}
        
        [data-testid="column"] {{
            padding: 8px 0;
        }}
        
        .sidebar-section {{
            padding: 12px;
            margin-bottom: 12px;
        }}
    }}
    </style>
    
    <script>
    (function() {{
        // Theme colors based on current session state
        const isDarkMode = {str(st.session_state.theme_mode == 'dark').lower()};
        
        const colors = isDarkMode ? {{
            bg: '#161b22',
            text: '#c9d1d9',
            border: '#30363d'
        }} : {{
            bg: '#f6f8fa',
            text: '#24292f',
            border: '#d0d7de'
        }};
        
        function updateStyles() {{
            // Update all select elements
            document.querySelectorAll('select').forEach(select => {{
                select.style.setProperty('background-color', colors.bg, 'important');
                select.style.setProperty('color', colors.text, 'important');
                select.style.setProperty('border-color', colors.border, 'important');
            }});
            
            // Update all button elements
            document.querySelectorAll('button').forEach(btn => {{
                btn.style.setProperty('background-color', colors.bg, 'important');
                btn.style.setProperty('color', colors.text, 'important');
                btn.style.setProperty('border-color', colors.border, 'important');
            }});
            
            // Update Select components (React Select)
            document.querySelectorAll('.Select-control').forEach(el => {{
                el.style.setProperty('background-color', colors.bg, 'important');
                el.style.setProperty('color', colors.text, 'important');
                el.style.setProperty('border-color', colors.border, 'important');
            }});
            
            document.querySelectorAll('.Select-menu').forEach(el => {{
                el.style.setProperty('background-color', colors.bg, 'important');
                el.style.setProperty('color', colors.text, 'important');
            }});
            
            document.querySelectorAll('.Select-option').forEach(el => {{
                el.style.setProperty('background-color', colors.bg, 'important');
                el.style.setProperty('color', colors.text, 'important');
            }});
            
            document.querySelectorAll('.Select-value').forEach(el => {{
                el.style.setProperty('color', colors.text, 'important');
            }});
            
            document.querySelectorAll('.Select-placeholder').forEach(el => {{
                el.style.setProperty('color', colors.text, 'important');
            }});
        }}
        
        // Run on load
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', updateStyles);
        }} else {{
            updateStyles();
        }}
        
        // Run periodically to catch dynamically added elements
        setInterval(updateStyles, 500);
        
        // Run on any DOM changes
        const observer = new MutationObserver(updateStyles);
        observer.observe(document.body, {{ childList: true, subtree: true }});
    }})();
    </script>
    """
    st.markdown(theme_css, unsafe_allow_html=True)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_risk_score(current: float, temperature: float) -> int:
    """
    Calculate risk score (0-100) based on current and temperature.
    
    SAFE (0-33): current < 5A AND temp < 40°C
    WARNING (34-66): current 5-10A OR temp 40-60°C
    CRITICAL (67-100): current > 10A OR temp > 60°C
    """
    # Normalize current (0-15A scale, capped at 15A for hardware cutoff)
    current_score = min((current / 15.0) * 50, 50)
    
    # Normalize temperature (0-75°C scale, capped at 75°C for hardware cutoff)
    temp_score = min((temperature / 75.0) * 50, 50)
    
    # Combined risk score
    risk_score = int(current_score + temp_score)
    return min(max(risk_score, 0), 100)


def get_state_color(state: str) -> str:
    """Return color for state indicator"""
    colors = get_colors()
    if state == "SAFE":
        return colors["safe"]
    elif state == "WARNING":
        return colors["warning"]
    elif state == "CRITICAL":
        return colors["critical"]
    else:
        return colors["text_secondary"]


def get_state_emoji(state: str) -> str:
    """Return emoji for state"""
    if state == "SAFE":
        return "OK"
    elif state == "WARNING":
        return "WARN"
    elif state == "CRITICAL":
        return "ALERT"
    else:
        return "?"


def get_relay_color(relay_status: str) -> str:
    """Return color for relay indicator"""
    colors = get_colors()
    if relay_status == "ON":
        return colors["safe"]
    elif relay_status == "OFF":
        return colors["critical"]
    else:
        return colors["text_secondary"]


def format_event_log(event_log: list, limit: int = 10) -> list:
    """Format event log for display"""
    formatted = []
    for event in event_log[-limit:]:
        formatted.append({
            "Time": event.timestamp.strftime("%H:%M:%S"),
            "Event": event.event_type,
            "State": event.state,
            "Relay": event.relay,
            "Current (A)": f"{event.current:.2f}",
            "Temp (°C)": f"{event.temperature:.2f}",
        })
    return list(reversed(formatted))


def format_uptime(seconds: float) -> str:
    """Format uptime in HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def create_themed_line_chart(data: list, title: str, color: str, unit: str = ""):
    """Create a themed line chart using Plotly"""
    colors = get_colors()
    
    # Convert hex to rgba for fill color with opacity
    def hex_to_rgba(hex_color, alpha=0.12):
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f'rgba({r}, {g}, {b}, {alpha})'
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=list(range(len(data))),
        y=data,
        mode='lines',
        line=dict(color=color, width=2),
        fill='tozeroy',
        fillcolor=hex_to_rgba(color, 0.12)
    ))
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=14, color=colors['text_primary']),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor=colors['border'],
            tickfont=dict(color=colors['text_secondary']),
            showline=False,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=colors['border'],
            tickfont=dict(color=colors['text_secondary']),
            showline=False,
        ),
        plot_bgcolor=colors['chart_bg'],
        paper_bgcolor=colors['chart_bg'],
        font=dict(color=colors['text_primary']),
        margin=dict(l=0, r=0, t=40, b=0),
        height=300,
        showlegend=False
    )
    
    return fig


def run_decision_cycle():
    """Execute one decision cycle and update session state"""
    try:
        system_state = st.session_state.app.run_decision_cycle()
        st.session_state.cycle_count += 1
        
        # Update history for charts
        if system_state:
            st.session_state.current_history.append(system_state.current)
            st.session_state.temp_history.append(system_state.temperature)
            st.session_state.state_history.append(system_state.state)
            st.session_state.timestamp_history.append(datetime.now())
        
        return system_state
    except Exception as e:
        st.error(f"Decision engine error: {e}")
        return None


# ============================================================================
# MAIN DASHBOARD LAYOUT
# ============================================================================

# Apply theme CSS
apply_theme_css()

# Sidebar Navigation
with st.sidebar:
    colors = get_colors()
    
    # Header section with branding
    st.markdown(f"""
    <div class='sidebar-header'>
        <div style='font-size: 28px; margin-bottom: 8px;'>⚡</div>
        <div style='font-size: 20px; font-weight: 700; color: {colors['text_primary']};'>VoltGuard</div>
        <div style='font-size: 12px; color: {colors['text_secondary']}; margin-top: 4px;'>Electrical Safety System</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Theme toggle section
    st.markdown(f"""
    <div class='sidebar-section'>
        <div class='sidebar-section-title'>Appearance</div>
    </div>
    """, unsafe_allow_html=True)
    
    theme_col1, theme_col2 = st.columns([3, 1], gap="small")
    with theme_col1:
        st.markdown(f"<span style='color: {colors['text_secondary']}; font-size: 13px;'>Theme</span>", unsafe_allow_html=True)
    with theme_col2:
        current_theme = "🌙" if st.session_state.theme_mode == "dark" else "☀️"
        if st.button(current_theme, use_container_width=True, key="theme_toggle", help="Toggle between Dark and Light themes"):
            st.session_state.theme_mode = "light" if st.session_state.theme_mode == "dark" else "dark"
            st.rerun()
    
    # Navigation section
    st.markdown(f"""
    <div class='sidebar-section'>
        <div class='sidebar-section-title'>Navigation</div>
    </div>
    """, unsafe_allow_html=True)
    
    page = st.radio(
        "",
        options=["Dashboard", "Live Data", "Alerts Log", "Settings", "About"],
        label_visibility="collapsed"
    )
    
    # Device status section
    st.markdown(f"""
    <div class='sidebar-section'>
        <div class='sidebar-section-title'>Device Status</div>
    </div>
    """, unsafe_allow_html=True)
    
    app_summary = st.session_state.app.get_summary()
    
    # Connection status with indicator
    status_color = colors["safe"]
    st.markdown(f"""
    <div style='display: flex; align-items: center; margin-bottom: 12px;'>
        <span class='status-indicator' style='background-color: {status_color};'></span>
        <span style='color: {colors['text_primary']}; font-size: 14px; font-weight: 500;'>Connected</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Device info cards
    st.markdown(f"""
    <div style='background-color: {colors['bg_secondary']}; border: 1px solid {colors['border']}; border-radius: 8px; padding: 12px; margin-bottom: 8px;'>
        <div style='color: {colors['text_secondary']}; font-size: 11px; margin-bottom: 4px;'>DEVICE TYPE</div>
        <div style='color: {colors['text_primary']}; font-size: 14px; font-weight: 600;'>Arduino UNO</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style='background-color: {colors['bg_secondary']}; border: 1px solid {colors['border']}; border-radius: 8px; padding: 12px; margin-bottom: 8px;'>
        <div style='color: {colors['text_secondary']}; font-size: 11px; margin-bottom: 4px;'>SIMULATOR MODE</div>
        <div style='color: {colors['text_primary']}; font-size: 14px; font-weight: 600;'>{st.session_state.simulator_mode.upper()}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # System status section
    st.markdown(f"""
    <div class='sidebar-section'>
        <div class='sidebar-section-title'>System Status</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Lockout warning
    if st.session_state.app.decision_engine.locked_out:
        st.markdown(f"""
        <div style='background-color: rgba(255, 23, 68, 0.1); border: 1px solid {colors['critical']}; border-radius: 8px; padding: 12px;'>
            <div style='color: {colors['critical']}; font-size: 13px; font-weight: 600; margin-bottom: 4px;'>⚠️ SYSTEM LOCKED</div>
            <div style='color: {colors['text_secondary']}; font-size: 11px;'>Manual reset required</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style='background-color: rgba(34, 197, 94, 0.1); border: 1px solid {colors['safe']}; border-radius: 8px; padding: 12px;'>
            <div style='color: {colors['safe']}; font-size: 13px; font-weight: 600; margin-bottom: 4px;'>✓ System Operational</div>
            <div style='color: {colors['text_secondary']}; font-size: 11px;'>All systems normal</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Quick stats at bottom
    st.markdown(f"""
    <div class='sidebar-section'>
        <div class='sidebar-section-title'>Quick Stats</div>
    </div>
    """, unsafe_allow_html=True)
    
    uptime = format_uptime(app_summary["uptime_seconds"])
    st.markdown(f"""
    <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'>
        <span style='color: {colors['text_secondary']}; font-size: 12px;'>Uptime</span>
        <span style='color: {colors['text_primary']}; font-size: 12px; font-weight: 500;'>{uptime}</span>
    </div>
    <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'>
        <span style='color: {colors['text_secondary']}; font-size: 12px;'>Cycles</span>
        <span style='color: {colors['text_primary']}; font-size: 12px; font-weight: 500;'>{app_summary['cycles']}</span>
    </div>
    <div style='display: flex; justify-content: space-between;'>
        <span style='color: {colors['text_secondary']}; font-size: 12px;'>Events</span>
        <span style='color: {colors['text_primary']}; font-size: 12px; font-weight: 500;'>{app_summary['events']}</span>
    </div>
    """, unsafe_allow_html=True)


# Main content area
colors = get_colors()

# Run one decision cycle
system_state = run_decision_cycle()

if system_state is None:
    st.warning("System initializing...")
    st.stop()

# ============================================================================
# PAGE: DASHBOARD (Main Monitoring View)
# ============================================================================

if page == "Dashboard":
    
    # Page title
    st.title("VoltGuard Dashboard")
    st.markdown("**Real-time Electrical Safety Monitoring**")
    
    # ======================================================================
    # STATE BANNER (System Status Overview)
    # ======================================================================
    
    risk_score = calculate_risk_score(system_state.current, system_state.temperature)
    
    banner_col1, banner_col2, banner_col3, banner_col4 = st.columns(4)
    
    with banner_col1:
        state_color = get_state_color(system_state.state)
        st.markdown(f"""
        <div style='background-color: {colors["bg_secondary"]}; border: 1px solid {colors["border"]}; padding: 24px; border-radius: 12px; height: 140px; display: flex; flex-direction: column; justify-content: space-between;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div style='color: {colors["text_secondary"]}; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;'>SYSTEM STATUS</div>
                <div style='width: 10px; height: 10px; border-radius: 50%; background-color: {state_color};'></div>
            </div>
            <div style='color: {state_color}; font-size: 32px; font-weight: 700;'>{system_state.state}</div>
            <div style='color: {colors["text_secondary"]}; font-size: 13px;'>System Online</div>
        </div>
        """, unsafe_allow_html=True)
    
    with banner_col2:
        # Risk score (0-100)
        risk_color = get_state_color("CRITICAL" if risk_score > 66 else "WARNING" if risk_score > 33 else "SAFE")
        st.markdown(f"""
        <div style='background-color: {colors["bg_secondary"]}; border: 1px solid {colors["border"]}; padding: 24px; border-radius: 12px; height: 140px; display: flex; flex-direction: column; justify-content: space-between;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div style='color: {colors["text_secondary"]}; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;'>RISK SCORE</div>
                <div style='width: 10px; height: 10px; border-radius: 50%; background-color: {risk_color};'></div>
            </div>
            <div style='color: {risk_color}; font-size: 32px; font-weight: 700;'>{risk_score}/100</div>
            <div>
                <div style='color: {colors["text_secondary"]}; font-size: 13px; margin-bottom: 6px;'>
                    {'Low Risk' if risk_score <= 33 else 'Medium Risk' if risk_score <= 66 else 'High Risk'}
                </div>
                <div style='width: 100%; background-color: {colors["border"]}; height: 6px; border-radius: 3px; overflow: hidden;'>
                    <div style='background-color: {risk_color}; width: {risk_score}%; height: 100%; border-radius: 3px;'></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with banner_col3:
        relay_color = get_relay_color(system_state.relay_status)
        relay_text = "Power ON" if system_state.relay_status == "ON" else "Power OFF"
        st.markdown(f"""
        <div style='background-color: {colors["bg_secondary"]}; border: 1px solid {colors["border"]}; padding: 24px; border-radius: 12px; height: 140px; display: flex; flex-direction: column; justify-content: space-between;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div style='color: {colors["text_secondary"]}; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;'>RELAY STATUS</div>
                <div style='width: 10px; height: 10px; border-radius: 50%; background-color: {relay_color};'></div>
            </div>
            <div style='color: {relay_color}; font-size: 32px; font-weight: 700;'>{relay_text}</div>
            <div style='color: {colors["text_secondary"]}; font-size: 13px;'>{'Power flowing' if system_state.relay_status == 'ON' else 'Power disconnected'}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with banner_col4:
        alert_count = len([e for e in st.session_state.app.get_event_log() if "CRITICAL" in e.event_type or "Alert" in e.event_type])
        alert_color = colors["critical"] if alert_count > 0 else colors["safe"]
        st.markdown(f"""
        <div style='background-color: {colors["bg_secondary"]}; border: 1px solid {colors["border"]}; padding: 24px; border-radius: 12px; height: 140px; display: flex; flex-direction: column; justify-content: space-between;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div style='color: {colors["text_secondary"]}; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;'>ACTIVE ALERTS</div>
                <div style='width: 10px; height: 10px; border-radius: 50%; background-color: {alert_color};'></div>
            </div>
            <div style='color: {alert_color}; font-size: 32px; font-weight: 700;'>{alert_count}</div>
            <div style='color: {colors["text_secondary"]}; font-size: 13px;'>
                {'No alerts' if alert_count == 0 else f'{alert_count} active'}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # ======================================================================
    # LIVE METRICS & CHARTS (Responsive Layout)
    # ======================================================================
    
    # Top row: Current & Temperature metrics
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    
    with metric_col1:
        st.metric(label="Current", value=f"{system_state.current:.2f} A", delta=None)
    
    with metric_col2:
        st.metric(label="Temperature", value=f"{system_state.temperature:.2f} °C", delta=None)
    
    with metric_col3:
        uptime = app_summary["uptime_seconds"]
        st.metric(label="Uptime", value=format_uptime(uptime))
    
    with metric_col4:
        st.metric(label="Data Cycle", value=f"{app_summary['cycles']}", delta=None)
    
    st.divider()
    
    # Charts row (responsive: 2 columns on desktop, 1 on mobile)
    chart_col1, chart_col2 = st.columns(2, gap="medium")
    
    with chart_col1:
        if len(st.session_state.current_history) > 0:
            current_color = get_state_color("CRITICAL" if system_state.current > 10 else "WARNING" if system_state.current > 5 else "SAFE")
            fig = create_themed_line_chart(
                list(st.session_state.current_history),
                "Current Trend",
                current_color
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Waiting for data...")
    
    with chart_col2:
        if len(st.session_state.temp_history) > 0:
            temp_color = get_state_color("CRITICAL" if system_state.temperature > 60 else "WARNING" if system_state.temperature > 40 else "SAFE")
            fig = create_themed_line_chart(
                list(st.session_state.temp_history),
                "Temperature Trend",
                temp_color
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Waiting for data...")
    
    st.divider()
    
    # ======================================================================
    # SAFETY FLAGS & SYSTEM INFO
    # ======================================================================
    
    flag_col1, flag_col2, flag_col3 = st.columns(3)
    
    with flag_col1:
        if system_state.anomaly_detected:
            st.error("ANOMALY DETECTED - Rate of change spike")
        else:
            st.success("No anomaly detected")
    
    with flag_col2:
        if system_state.hardware_override_triggered:
            st.error("HARDWARE OVERRIDE ACTIVE")
        else:
            st.success("Hardware override not triggered")
    
    with flag_col3:
        if st.session_state.app.decision_engine.locked_out:
            st.error("SYSTEM LOCKED OUT")
        else:
            st.success("System operational")
    
    st.divider()
    
    # ======================================================================
    # OPERATING THRESHOLDS
    # ======================================================================
    
    st.markdown("### Operating Thresholds")
    st.markdown("The system monitors your electrical parameters against these operational limits:")
    
    threshold_col1, threshold_col2, threshold_col3, threshold_col4 = st.columns(4)
    
    with threshold_col1:
        st.markdown(f"""
        <div style='background-color: {colors["bg_secondary"]}; border: 1px solid {colors["border"]}; padding: 20px; border-radius: 12px; height: 100%;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
                <div style='color: {colors["text_secondary"]}; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;'>SAFE ZONE</div>
                <div style='width: 8px; height: 8px; border-radius: 50%; background-color: {colors["safe"]};'></div>
            </div>
            <div style='color: {colors["text_primary"]}; font-size: 13px; margin-bottom: 8px;'>
                <span style='color: {colors["text_secondary"]};'>Current:</span> &lt; 5.0A
            </div>
            <div style='color: {colors["text_primary"]}; font-size: 13px;'>
                <span style='color: {colors["text_secondary"]};'>Temperature:</span> &lt; 40.0°C
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with threshold_col2:
        st.markdown(f"""
        <div style='background-color: {colors["bg_secondary"]}; border: 1px solid {colors["border"]}; padding: 20px; border-radius: 12px; height: 100%;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
                <div style='color: {colors["text_secondary"]}; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;'>WARNING ZONE</div>
                <div style='width: 8px; height: 8px; border-radius: 50%; background-color: {colors["warning"]};'></div>
            </div>
            <div style='color: {colors["text_primary"]}; font-size: 13px; margin-bottom: 8px;'>
                <span style='color: {colors["text_secondary"]};'>Current:</span> 5.0 - 10.0A
            </div>
            <div style='color: {colors["text_primary"]}; font-size: 13px;'>
                <span style='color: {colors["text_secondary"]};'>Temperature:</span> 40.0 - 60.0°C
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with threshold_col3:
        st.markdown(f"""
        <div style='background-color: {colors["bg_secondary"]}; border: 1px solid {colors["border"]}; padding: 20px; border-radius: 12px; height: 100%;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
                <div style='color: {colors["text_secondary"]}; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;'>CRITICAL ZONE</div>
                <div style='width: 8px; height: 8px; border-radius: 50%; background-color: {colors["critical"]};'></div>
            </div>
            <div style='color: {colors["text_primary"]}; font-size: 13px; margin-bottom: 8px;'>
                <span style='color: {colors["text_secondary"]};'>Current:</span> &gt; 10.0A
            </div>
            <div style='color: {colors["text_primary"]}; font-size: 13px;'>
                <span style='color: {colors["text_secondary"]};'>Temperature:</span> &gt; 60.0°C
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with threshold_col4:
        st.markdown(f"""
        <div style='background-color: {colors["bg_secondary"]}; border: 1px solid {colors["border"]}; padding: 20px; border-radius: 12px; height: 100%;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
                <div style='color: {colors["text_secondary"]}; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;'>HARDWARE LIMIT</div>
                <div style='width: 8px; height: 8px; border-radius: 50%; background-color: {colors["critical"]};'></div>
            </div>
            <div style='color: {colors["text_primary"]}; font-size: 13px; margin-bottom: 8px;'>
                <span style='color: {colors["text_secondary"]};'>Current:</span> &gt; 15.0A
            </div>
            <div style='color: {colors["text_primary"]}; font-size: 13px;'>
                <span style='color: {colors["text_secondary"]};'>Temperature:</span> &gt; 75.0°C
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # ======================================================================
    # RECENT EVENTS
    # ======================================================================
    
    st.markdown("### Recent Events")
    
    event_log = st.session_state.app.get_event_log()
    
    if event_log:
        formatted_events = format_event_log(event_log, limit=10)
        
        event_df = pd.DataFrame(formatted_events)
        st.dataframe(event_df, use_container_width=True, height=300)
        
        st.caption(f"Showing last 10 of {len(event_log)} events")
    else:
        st.info("No events logged yet")
    
    st.divider()
    
    # ======================================================================
    # SYSTEM INFORMATION (Bottom Section)
    # ======================================================================
    
    st.markdown("### System Information")
    
    info_col1, info_col2, info_col3 = st.columns(3)
    
    with info_col1:
        st.metric("Decision Cycles", app_summary["cycles"])
    
    with info_col2:
        st.metric("Events Logged", app_summary["events"])
    
    with info_col3:
        st.metric("System Errors", app_summary["errors"])
    
    st.caption(f"Active simulator mode: {st.session_state.simulator_mode} | Theme: {st.session_state.theme_mode}")


# ============================================================================
# PAGE: LIVE DATA (Expanded Charts & Statistics)
# ============================================================================

elif page == "Live Data":
    st.title("Live Data")
    st.markdown("Detailed real-time sensor data and statistics")
    
    # Simulator mode selector
    mode_options = ["stable", "rising_current", "rising_temp", "fault"]
    selected_mode = st.selectbox(
        "Simulator Mode",
        options=mode_options,
        index=mode_options.index(st.session_state.simulator_mode),
        help="Select simulator input pattern for testing scenarios.",
    )
    
    if selected_mode != st.session_state.simulator_mode:
        st.session_state.app.stop()
        st.session_state.simulator_mode = selected_mode
        st.session_state.app = VoltGuardApplication(
            use_simulator=True,
            simulator_mode=st.session_state.simulator_mode,
            enable_logging=True,
        )
        st.session_state.last_update_time = time.time()
        st.session_state.cycle_count = 0
        st.rerun()
    
    st.divider()
    
    # Expanded charts
    st.markdown("### Current & Temperature Trends")
    
    live_col1, live_col2 = st.columns(2)
    
    with live_col1:
        if len(st.session_state.current_history) > 0:
            current_color = get_state_color("CRITICAL" if system_state.current > 10 else "WARNING" if system_state.current > 5 else "SAFE")
            fig = create_themed_line_chart(
                list(st.session_state.current_history),
                "Current (A)",
                current_color
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Waiting for data...")
    
    with live_col2:
        if len(st.session_state.temp_history) > 0:
            temp_color = get_state_color("CRITICAL" if system_state.temperature > 60 else "WARNING" if system_state.temperature > 40 else "SAFE")
            fig = create_themed_line_chart(
                list(st.session_state.temp_history),
                "Temperature (°C)",
                temp_color
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Waiting for data...")
    
    st.divider()
    
    # Statistics
    st.markdown("### Statistics")
    
    if len(st.session_state.current_history) > 0:
        current_list = list(st.session_state.current_history)
        temp_list = list(st.session_state.temp_history)
        
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        
        with stat_col1:
            st.metric("Current Min", f"{min(current_list):.2f} A")
            st.metric("Current Max", f"{max(current_list):.2f} A")
            st.metric("Current Avg", f"{sum(current_list)/len(current_list):.2f} A")
        
        with stat_col2:
            st.metric("Temp Min", f"{min(temp_list):.2f} °C")
            st.metric("Temp Max", f"{max(temp_list):.2f} °C")
            st.metric("Temp Avg", f"{sum(temp_list)/len(temp_list):.2f} °C")
        
        with stat_col3:
            st.metric("Total Cycles", st.session_state.cycle_count)
            st.metric("Data Points", len(current_list))
            st.metric("Errors", st.session_state.app.get_summary()["errors"])


# ============================================================================
# PAGE: ALERTS LOG
# ============================================================================

elif page == "Alerts Log":
    st.title("Alerts Log")
    st.markdown("Complete event history with severity indicators")
    
    event_log = st.session_state.app.get_event_log()
    
    if event_log:
        formatted_events = format_event_log(event_log, limit=None)
        
        # Filter options
        filter_col1, filter_col2 = st.columns(2)
        
        with filter_col1:
            event_types = list(set([e["Event"] for e in formatted_events]))
            selected_event_type = st.multiselect(
                "Filter by Event Type",
                options=event_types,
                default=event_types
            )
        
        with filter_col2:
            state_types = list(set([e["State"] for e in formatted_events]))
            selected_state = st.multiselect(
                "Filter by State",
                options=state_types,
                default=state_types
            )
        
        # Apply filters
        filtered_events = [
            e for e in formatted_events
            if e["Event"] in selected_event_type and e["State"] in selected_state
        ]
        
        event_df = pd.DataFrame(filtered_events)
        st.dataframe(event_df, use_container_width=True)
        
        st.caption(f"Showing {len(filtered_events)} of {len(event_log)} events")
    else:
        st.info("No events logged yet")


# ============================================================================
# PAGE: SYSTEM SETTINGS
# ============================================================================

elif page == "Settings":
    st.title("System Settings")
    
    # Simulator mode selector
    st.markdown("### Simulator Configuration")
    
    mode_options = ["stable", "rising_current", "rising_temp", "fault"]
    selected_mode = st.selectbox(
        "Simulator Mode",
        options=mode_options,
        index=mode_options.index(st.session_state.simulator_mode),
        help="Select simulator input pattern for testing scenarios.",
    )
    
    if selected_mode != st.session_state.simulator_mode:
        st.session_state.app.stop()
        st.session_state.simulator_mode = selected_mode
        st.session_state.app = VoltGuardApplication(
            use_simulator=True,
            simulator_mode=st.session_state.simulator_mode,
            enable_logging=True,
        )
        st.session_state.last_update_time = time.time()
        st.session_state.cycle_count = 0
        st.rerun()
    
    st.success(f"Simulator mode: {st.session_state.simulator_mode}")
    
    st.divider()
    
    # Thresholds (read-only)
    st.markdown("### System Thresholds (Read-Only)")
    
    st.info("""
    **Threshold Values (Cannot be modified from UI):**
    
    - **SAFE**: Current < 5.0A AND Temperature < 40.0°C
    - **WARNING**: Current 5.0-10.0A OR Temperature 40.0-60.0°C
    - **CRITICAL**: Current > 10.0A OR Temperature > 60.0°C
    - **HARDWARE CUTOFF**: Current > 15.0A OR Temperature > 75.0°C
    
    To modify thresholds, edit the configuration file in `/config/config.py`
    """)
    
    st.divider()
    
    # System reset (lockout status)
    st.markdown("### System Status")
    
    app_summary = st.session_state.app.get_summary()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("System Locked Out", "Yes" if app_summary["locked_out"] else "No")
    
    with col2:
        st.metric("Uptime", format_uptime(app_summary["uptime_seconds"]))
    
    with col3:
        st.metric("Total Cycles", app_summary["cycles"])
    
    if app_summary["locked_out"]:
        st.warning("System is currently locked out due to critical shutdown. Manual reset may be required.")


# ============================================================================
# PAGE: ABOUT
# ============================================================================

elif page == "About":
    st.title("About VoltGuard")
    
    st.markdown("""
    ### VoltGuard - Electrical Safety System
    
    An intelligent electrical monitoring and protection system that:
    
    - Continuously monitors electrical current and temperature
    - Uses AI decision logic to detect anomalies and classify system state
    - Automatically cuts power when safety thresholds are exceeded
    - Provides real-time dashboard visualization
    - Sends SMS alerts for critical events
    
    #### System Architecture
    
    - **Hardware**: Arduino/ESP32 with current and temperature sensors
    - **Engine**: Python-based decision engine with anomaly detection
    - **Dashboard**: Real-time Streamlit visualization
    - **Notifications**: SMS alerts via Arkesel API
    
    #### Safety Features
    
    - Hardware-enforced safety override (independent of AI)
    - Fail-safe timeout (power cut if no signal for 3 seconds)
    - Lockout mechanism (no auto-recovery after critical shutdown)
    - Dual-layer protection (hardware + software)
    
    #### System Thresholds
    
    | Zone | Current | Temperature |
    |------|---------|-------------|
    | Safe | < 5.0A | < 40.0°C |
    | Warning | 5.0-10.0A | 40.0-60.0°C |
    | Critical | > 10.0A | > 60.0°C |
    | Hardware Limit | > 15.0A | > 75.0°C |
    
    ---
    
    **Version**: Phase 1D (Dashboard Redesign)
    **Theme**: """ + st.session_state.theme_mode.capitalize() + """
    **Status**: Operational
    """)


# ============================================================================
# AUTO-REFRESH MECHANISM (CONTROLLED)
# ============================================================================

# Controlled refresh: update every 1-2 seconds
current_time = time.time()
elapsed = current_time - st.session_state.last_update_time

if elapsed >= 1.5:  # Refresh every 1.5 seconds
    st.session_state.last_update_time = current_time
    st.rerun()
else:
    time.sleep(0.1)  # Small delay to prevent CPU spinning
    # Calculate remaining sleep time
    remaining_sleep = 1.5 - elapsed
    time.sleep(max(0.1, remaining_sleep / 2))  # Don't block completely


# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.caption(f"VoltGuard Phase 1D Dashboard | Cycle #{st.session_state.app.cycle_count} | Last update: {datetime.now().strftime('%H:%M:%S')}")


# ============================================================================
# CLEANUP (GRACEFUL SHUTDOWN)
# ============================================================================

# Note: Streamlit will call this on session termination
import atexit

def cleanup():
    """Graceful shutdown on dashboard close"""
    if "app" in st.session_state:
        st.session_state.app.stop()

atexit.register(cleanup)
