import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtCore

ApplicationWindow {
    id: win
    width: 1120
    height: 740
    minimumWidth: 640
    minimumHeight: 480
    visible: true
    title: "Ruqya Quran"
    color: theme.bg

    property real fontScale: 1.0
    property bool sidebarOpen: true
    readonly property bool wide: width >= 940
    readonly property int sidebarWidth: 340

    function fmt(ms) {
        var s = Math.max(0, Math.floor(ms / 1000))
        return Math.floor(s / 60) + ":" + ("0" + (s % 60)).slice(-2)
    }

    // ------------------------------------------------ theme
    QtObject {
        id: theme
        property bool dark: Application.styleHints.colorScheme !== Qt.ColorScheme.Light
        readonly property color bg:         dark ? "#13171b" : "#faf7f2"
        readonly property color surface:    dark ? "#1b2025" : "#ffffff"
        readonly property color surfaceAlt: dark ? "#242b31" : "#f1ece3"
        readonly property color text:       dark ? "#e9e6e0" : "#1d2125"
        readonly property color textDim:    dark ? "#98a1a8" : "#6b6f73"
        readonly property color accent:     dark ? "#5fbf9f" : "#1f7a5c"
        readonly property color onAccent:   dark ? "#0b1512" : "#ffffff"
        readonly property color line:       dark ? "#2a3238" : "#e2dccf"
        readonly property color danger:     "#d9534f"
    }

    Settings {
        category: "ui"
        property alias dark: theme.dark
        property alias fontScale: win.fontScale
        property alias sidebarOpen: win.sidebarOpen
    }

    // ------------------------------------------------ reusable pieces
    component Icon: Canvas {
        id: ic
        property string kind: "play"
        property color color: "white"
        implicitWidth: 24
        implicitHeight: 24
        renderTarget: Canvas.FramebufferObject
        onColorChanged: requestPaint()
        onKindChanged: requestPaint()
        onWidthChanged: requestPaint()
        onPaint: {
            var c = getContext("2d")
            c.reset()
            c.clearRect(0, 0, width, height)
            var s = width / 24
            c.scale(s, s)
            c.fillStyle = color
            c.strokeStyle = color
            c.lineWidth = 2
            c.lineCap = "round"
            if (kind === "play") {
                c.beginPath(); c.moveTo(7, 4); c.lineTo(20, 12); c.lineTo(7, 20); c.closePath(); c.fill()
            } else if (kind === "pause") {
                c.fillRect(6, 4, 4, 16); c.fillRect(14, 4, 4, 16)
            } else if (kind === "next") {
                c.beginPath(); c.moveTo(5, 5); c.lineTo(15, 12); c.lineTo(5, 19); c.closePath(); c.fill()
                c.fillRect(16.5, 5, 2.5, 14)
            } else if (kind === "prev") {
                c.beginPath(); c.moveTo(19, 5); c.lineTo(9, 12); c.lineTo(19, 19); c.closePath(); c.fill()
                c.fillRect(5, 5, 2.5, 14)
            } else if (kind === "volume" || kind === "muted") {
                c.beginPath()
                c.moveTo(3, 9); c.lineTo(7, 9); c.lineTo(12, 5); c.lineTo(12, 19); c.lineTo(7, 15); c.lineTo(3, 15)
                c.closePath(); c.fill()
                if (kind === "volume") {
                    c.beginPath(); c.arc(12, 12, 5, -0.9, 0.9); c.stroke()
                    c.beginPath(); c.arc(12, 12, 9, -0.8, 0.8); c.stroke()
                } else {
                    c.beginPath(); c.moveTo(16, 9); c.lineTo(22, 15); c.moveTo(22, 9); c.lineTo(16, 15); c.stroke()
                }
            }
        }
    }

    component IconButton: AbstractButton {
        id: ib
        property var t
        property int size: 40
        property string iconKind: ""
        property bool accent: false
        property string tip: ""
        implicitWidth: size
        implicitHeight: size
        focusPolicy: Qt.NoFocus
        hoverEnabled: true
        contentItem: Item {
            Text {
                anchors.centerIn: parent
                visible: ib.iconKind === ""
                text: ib.text
                font.pixelSize: ib.size * 0.42
                color: ib.accent ? ib.t.onAccent : ib.t.text
            }
            Icon {
                anchors.centerIn: parent
                visible: ib.iconKind !== ""
                kind: ib.iconKind
                width: ib.size * 0.42
                height: width
                color: ib.accent ? ib.t.onAccent : ib.t.text
            }
        }
        background: Rectangle {
            radius: width / 2
            color: ib.accent ? ib.t.accent
                 : ib.down ? ib.t.line
                 : ib.hovered ? ib.t.surfaceAlt : "transparent"
            scale: ib.accent && ib.down ? 0.95 : 1
        }
        ToolTip.visible: hovered && tip !== ""
        ToolTip.text: tip
        ToolTip.delay: 600
    }

    component Pill: AbstractButton {
        id: pl
        property var t
        property bool active: false
        focusPolicy: Qt.NoFocus
        hoverEnabled: true
        implicitHeight: 32
        implicitWidth: contentItem.implicitWidth + 28
        contentItem: Text {
            text: pl.text
            font.pixelSize: 13
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            color: pl.active ? pl.t.accent : pl.t.textDim
        }
        background: Rectangle {
            radius: height / 2
            color: pl.active ? Qt.alpha(pl.t.accent, 0.15) : (pl.hovered ? pl.t.surfaceAlt : "transparent")
            border.width: 1
            border.color: pl.active ? pl.t.accent : pl.t.line
        }
    }

    component Track: Slider {
        id: tr
        property var t
        focusPolicy: Qt.NoFocus
        implicitHeight: 20
        background: Rectangle {
            x: tr.leftPadding
            y: tr.topPadding + tr.availableHeight / 2 - height / 2
            width: tr.availableWidth
            height: 4
            radius: 2
            color: tr.t.line
            Rectangle {
                width: tr.visualPosition * parent.width
                height: parent.height
                radius: 2
                color: tr.t.accent
            }
        }
        handle: Rectangle {
            x: tr.leftPadding + tr.visualPosition * (tr.availableWidth - width)
            y: tr.topPadding + tr.availableHeight / 2 - height / 2
            width: 14; height: 14; radius: 7
            color: tr.t.accent
            scale: (tr.pressed || tr.hovered) ? 1 : 0
            Behavior on scale { NumberAnimation { duration: 120 } }
        }
    }

    // ------------------------------------------------ shortcuts
    Shortcut { sequence: "Space";       onActivated: player.toggle() }
    Shortcut { sequence: "Right";       onActivated: player.playNext() }
    Shortcut { sequence: "Left";        onActivated: player.playPrevious() }
    Shortcut { sequence: "Shift+Right"; onActivated: player.seekBy(5000) }
    Shortcut { sequence: "Shift+Left";  onActivated: player.seekBy(-5000) }
    Shortcut { sequence: "Up";          onActivated: player.volume = player.volume + 0.05 }
    Shortcut { sequence: "Down";        onActivated: player.volume = player.volume - 0.05 }
    Shortcut { sequence: "M";           onActivated: player.muted = !player.muted }
    Shortcut { sequence: "T";           onActivated: player.showTranslation = !player.showTranslation }
    Shortcut { sequence: "L";           onActivated: player.cycleRepeat() }
    Shortcut { sequence: "P";           onActivated: win.sidebarOpen = !win.sidebarOpen }
    Shortcut { sequences: ["+", "="];   onActivated: win.fontScale = Math.min(1.8, win.fontScale + 0.1) }
    Shortcut { sequence: "-";           onActivated: win.fontScale = Math.max(0.6, win.fontScale - 0.1) }

    Binding {
        target: seek
        property: "value"
        value: player.position
        when: !seek.pressed
    }

    Connections {
        target: player
        function onDisplayChanged() { fadeIn.restart(); flick.contentY = 0 }
        function onCurrentIndexChanged() {
            if (player.currentIndex >= 0)
                list.positionViewAtIndex(player.currentIndex, ListView.Contain)
        }
        function onToast(msg) { toastText.text = msg; toast.opacity = 1; toastTimer.restart() }
    }

    // ------------------------------------------------ layout
    Item {
        anchors.fill: parent

        // ============ main content ============
        Item {
            id: content
            anchors {
                top: parent.top; bottom: parent.bottom; right: parent.right; left: parent.left
                leftMargin: (win.wide && win.sidebarOpen) ? win.sidebarWidth : 0
            }
            Behavior on anchors.leftMargin { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }

            // ---- top bar
            Item {
                id: topBar
                height: 56
                anchors { top: parent.top; left: parent.left; right: parent.right }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 4

                    IconButton { t: theme; text: "☰"; tip: "Playlist (P)"
                        onClicked: win.sidebarOpen = !win.sidebarOpen }
                    Text {
                        text: "Ruqya"
                        visible: !(win.wide && win.sidebarOpen)
                        font.pixelSize: 16
                        font.weight: Font.DemiBold
                        color: theme.textDim
                    }
                    Item { Layout.fillWidth: true }

                    Pill {
                        t: theme
                        text: "Translation"
                        visible: player.hasTranslationEdition
                        active: player.showTranslation
                        onClicked: player.showTranslation = !player.showTranslation
                    }
                    IconButton { t: theme; text: "A−"; tip: "Smaller text (−)"
                        onClicked: win.fontScale = Math.max(0.6, win.fontScale - 0.1) }
                    IconButton { t: theme; text: "A+"; tip: "Larger text (+)"
                        onClicked: win.fontScale = Math.min(1.8, win.fontScale + 0.1) }
                    IconButton { t: theme; text: "◐"; tip: "Light / dark"
                        onClicked: theme.dark = !theme.dark }
                }
            }

            // ---- reading area
            Flickable {
                id: flick
                anchors { top: topBar.bottom; bottom: transport.top; left: parent.left; right: parent.right }
                clip: true
                contentWidth: width
                contentHeight: Math.max(height, col.implicitHeight + 80)
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { }

                ColumnLayout {
                    id: col
                    visible: player.currentIndex >= 0
                    width: Math.min(flick.width - 48, 860)
                    x: (flick.width - width) / 2
                    y: Math.max(32, (flick.height - implicitHeight) / 2)
                    spacing: 18

                    NumberAnimation { id: fadeIn; target: col; property: "opacity"
                        from: 0; to: 1; duration: 280; easing.type: Easing.OutQuad }

                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        visible: text !== ""
                        text: player.subtitle.toUpperCase()
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.6
                        color: theme.accent
                    }
                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 12
                        Text {
                            text: player.title
                            font.pixelSize: 22
                            font.weight: Font.DemiBold
                            color: theme.text
                        }
                        Text {
                            visible: text !== ""
                            text: player.titleArabic
                            font.family: player.fontFamily
                            font.pixelSize: 24
                            color: theme.textDim
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.topMargin: 8
                        text: player.arabicText
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                        font.family: player.fontFamily
                        font.pixelSize: Math.round(40 * win.fontScale)
                        lineHeight: 1.75
                        lineHeightMode: Text.ProportionalHeight
                        color: theme.text
                    }
                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter
                        visible: player.showTranslation && player.translationText !== ""
                        width: 48; height: 2; radius: 1
                        color: theme.accent
                        opacity: 0.6
                    }
                    Text {
                        Layout.fillWidth: true
                        visible: player.showTranslation && text !== ""
                        text: player.translationText
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: Math.round(20 * win.fontScale)
                        lineHeight: 1.4
                        lineHeightMode: Text.ProportionalHeight
                        color: theme.textDim
                    }
                }
            }

            // ---- empty / preparing state
            ColumnLayout {
                anchors.centerIn: flick
                visible: player.currentIndex < 0
                spacing: 6
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Preparing your playlist…"
                    font.pixelSize: 20
                    color: theme.text
                }
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "The first run downloads audio; after that it works offline."
                    font.pixelSize: 14
                    color: theme.textDim
                }
            }

            // ---- toast
            Rectangle {
                id: toast
                anchors { horizontalCenter: parent.horizontalCenter; bottom: transport.top; bottomMargin: 16 }
                opacity: 0
                visible: opacity > 0
                radius: 18
                color: theme.dark ? "#e9e6e0" : "#23282d"
                width: toastText.implicitWidth + 36
                height: 36
                Behavior on opacity { NumberAnimation { duration: 200 } }
                Text {
                    id: toastText
                    anchors.centerIn: parent
                    font.pixelSize: 13
                    color: theme.dark ? "#13171b" : "#ffffff"
                }
                Timer { id: toastTimer; interval: 3500; onTriggered: toast.opacity = 0 }
            }

            // ---- transport bar
            Rectangle {
                id: transport
                height: 112
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                color: theme.surface

                Rectangle { height: 1; width: parent.width; color: theme.line }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 20
                    anchors.rightMargin: 20
                    anchors.topMargin: 12
                    anchors.bottomMargin: 10
                    spacing: 4

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Text {
                            Layout.preferredWidth: 40
                            text: win.fmt(player.position)
                            font.pixelSize: 12
                            color: theme.textDim
                            horizontalAlignment: Text.AlignRight
                        }
                        Track {
                            id: seek
                            t: theme
                            Layout.fillWidth: true
                            from: 0
                            to: Math.max(1, player.duration)
                            enabled: player.duration > 0
                            onMoved: player.seek(Math.round(value))
                        }
                        Text {
                            Layout.preferredWidth: 40
                            text: win.fmt(player.duration)
                            font.pixelSize: 12
                            color: theme.textDim
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 8

                        // now playing
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            visible: content.width > 720
                            spacing: 0
                            Text {
                                Layout.fillWidth: true
                                text: player.title
                                elide: Text.ElideRight
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
                                color: theme.text
                            }
                            Text {
                                Layout.fillWidth: true
                                text: player.subtitle
                                elide: Text.ElideRight
                                font.pixelSize: 12
                                color: theme.textDim
                            }
                        }
                        Item { visible: content.width <= 720; Layout.fillWidth: true; Layout.preferredWidth: 1 }

                        // controls
                        RowLayout {
                            spacing: 14
                            IconButton { t: theme; size: 44; iconKind: "prev"; tip: "Previous (←)"
                                onClicked: player.playPrevious() }
                            IconButton {
                                t: theme; size: 56; accent: true
                                iconKind: player.isPlaying ? "pause" : "play"
                                tip: player.isPlaying ? "Pause (Space)" : "Play (Space)"
                                onClicked: player.toggle()
                            }
                            IconButton { t: theme; size: 44; iconKind: "next"; tip: "Next (→)"
                                onClicked: player.playNext() }
                        }

                        // repeat + volume
                        Item {
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            Layout.fillHeight: true
                            RowLayout {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 8
                                Pill {
                                    t: theme
                                    text: ["Repeat: off", "Repeat: one", "Repeat: all"][player.repeatMode]
                                    active: player.repeatMode > 0
                                    onClicked: player.cycleRepeat()
                                }
                                IconButton {
                                    t: theme; size: 36
                                    visible: content.width > 860
                                    iconKind: player.muted || player.volume === 0 ? "muted" : "volume"
                                    tip: "Mute (M)"
                                    onClicked: player.muted = !player.muted
                                }
                                Track {
                                    t: theme
                                    visible: content.width > 860
                                    Layout.preferredWidth: 90
                                    from: 0; to: 1
                                    value: player.volume
                                    onMoved: { player.muted = false; player.volume = value }
                                }
                            }
                        }
                    }
                }
            }
        }

        // ============ scrim (narrow windows) ============
        Rectangle {
            anchors.fill: parent
            z: 15
            color: "#000000"
            opacity: (!win.wide && win.sidebarOpen) ? 0.45 : 0
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: 200 } }
            MouseArea { anchors.fill: parent; onClicked: win.sidebarOpen = false }
        }

        // ============ sidebar ============
        Rectangle {
            id: sidebar
            z: 20
            width: win.sidebarWidth
            height: parent.height
            x: win.sidebarOpen ? 0 : -width
            color: theme.surface
            Behavior on x { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
            Rectangle { width: 1; height: parent.height; anchors.right: parent.right; color: theme.line }

            ColumnLayout {
                anchors.fill: parent
                anchors.rightMargin: 1
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 56
                    Layout.leftMargin: 16
                    Layout.rightMargin: 8
                    Text {
                        text: "Playlist"
                        Layout.fillWidth: true
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                        color: theme.text
                    }
                    IconButton { t: theme; size: 36; text: "◎"; tip: "Jump to current"
                        onClicked: list.positionViewAtIndex(Math.max(0, player.currentIndex), ListView.Center) }
                }

                ListView {
                    id: list
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: playlistModel
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar { }

                    section.property: "group"
                    section.criteria: ViewSection.FullString
                    section.labelPositioning: ViewSection.InlineLabels | ViewSection.CurrentLabelAtStart
                    section.delegate: Rectangle {
                        required property string section
                        width: list.width
                        height: 38
                        color: theme.surface
                        Text {
                            anchors { left: parent.left; leftMargin: 16; right: parent.right
                                      rightMargin: 16; bottom: parent.bottom; bottomMargin: 6 }
                            text: parent.section
                            elide: Text.ElideRight
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                            font.letterSpacing: 0.5
                            color: theme.textDim
                        }
                    }

                    delegate: ItemDelegate {
                        id: row
                        required property int index
                        required property string label
                        required property string status
                        required property string errorText
                        width: list.width
                        height: 44
                        focusPolicy: Qt.NoFocus
                        highlighted: row.index === player.currentIndex

                        background: Rectangle {
                            color: row.highlighted ? Qt.alpha(theme.accent, 0.14)
                                 : row.hovered ? theme.surfaceAlt : "transparent"
                            Rectangle {
                                visible: row.highlighted
                                width: 3; height: parent.height; color: theme.accent
                            }
                        }
                        contentItem: RowLayout {
                            spacing: 10
                            Item {
                                Layout.preferredWidth: 16
                                Layout.preferredHeight: 16
                                Icon {
                                    anchors.centerIn: parent
                                    width: 12; height: 12
                                    visible: row.highlighted
                                    kind: player.isPlaying ? "play" : "pause"
                                    color: theme.accent
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: row.label
                                elide: Text.ElideRight
                                font.pixelSize: 14
                                font.weight: row.highlighted ? Font.DemiBold : Font.Normal
                                color: row.status === "error" ? theme.danger
                                     : row.status === "loading" ? theme.textDim : theme.text
                            }
                            Text {
                                visible: row.status === "loading"
                                text: "…"
                                color: theme.textDim
                            }
                            Text {
                                visible: row.status === "error"
                                text: "⚠"
                                color: theme.danger
                            }
                        }
                        ToolTip.visible: hovered && errorText !== ""
                        ToolTip.text: errorText
                        ToolTip.delay: 400

                        onClicked: {
                            player.play(row.index)
                            if (!win.wide) win.sidebarOpen = false
                        }
                    }
                }

                // loading / failure footer
                Rectangle {
                    Layout.fillWidth: true
                    visible: player.loading || player.failedCount > 0
                    implicitHeight: footCol.implicitHeight + 24
                    color: theme.surfaceAlt

                    ColumnLayout {
                        id: footCol
                        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter
                                  leftMargin: 16; rightMargin: 16 }
                        spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                Layout.fillWidth: true
                                font.pixelSize: 12
                                color: theme.textDim
                                text: player.loading
                                      ? "Preparing audio… " + player.loadedCount + " / " + player.totalCount
                                      : player.failedCount + " item(s) failed to load"
                            }
                            Pill {
                                t: theme
                                visible: !player.loading && player.failedCount > 0
                                text: "Retry"
                                onClicked: player.retry()
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            visible: player.loading
                            height: 3; radius: 1.5
                            color: theme.line
                            Rectangle {
                                height: parent.height; radius: 1.5
                                color: theme.accent
                                width: player.totalCount > 0 ? parent.width * player.loadedCount / player.totalCount : 0
                                Behavior on width { NumberAnimation { duration: 150 } }
                            }
                        }
                    }
                }
            }
        }
    }
}
