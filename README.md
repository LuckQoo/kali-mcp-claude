sudo apt update && sudo apt upgrade -y && sudo apt install -y fuse libfuse2 wget curl git gnupg2 software-properties-common && sudo apt remove -y docker docker-engine docker.io containerd runc && curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian bookworm stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null && sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin && sudo systemctl start docker && sudo systemctl enable docker && sudo usermod -aG docker $USER && mkdir -p ~/Applications/claude-desktop && cd ~/Applications/claude-desktop && wget https://github.com/LibreTranslate/Claude-Desktop/releases/latest/download/Claude-Desktop-x86_64.AppImage && chmod +x Claude-Desktop-x86_64.AppImage && sudo bash -c 'cat > /usr/share/applications/claude-desktop.desktop << EOF
[Desktop Entry]
Name=Claude Desktop
Comment=Claude AI Desktop Client
Exec=/home/$USER/Applications/claude-desktop/Claude-Desktop-x86_64.AppImage
Icon=chatbot
Terminal=false
Type=Application
Categories=Utility;Network;Chat;
StartupWMClass=Claude Desktop
EOF'

cd ~/Applications/claude-desktop && wget https://github.com/LibreTranslate/Claude-Desktop/releases/latest/download/Claude-Desktop-x86_64.AppImage


https://lobehub.com/zh-TW/mcp/marklechner-kali-mcp-server
