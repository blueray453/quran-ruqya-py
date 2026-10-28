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
    property string themeName: "dark"          // "dark" | "light" (Solarized)
    property int focusWord: -1
    property var revealed: ({})
    readonly property bool wide: width >= 940
    readonly property int sidebarWidth: 340

    function fmt(ms) {
        var s = Math.max(0, Math.floor(ms / 1000))
        return Math.floor(s / 60) + ":" + ("0" + (s % 60)).slice(-2)
    }
    function reveal(i) {
        var r = {}
        for (var k in revealed) r[k] = true
        r[i] = true
        revealed = r
    }
    function ensureVisible(i) {
        var item = list.itemAtIndex(i)
        if (item && item.y >= list.contentY && item.y + item.height <= list.contentY + list.height)
            return                                  // already visible: don't move the panel
        list.positionViewAtIndex(i, ListView.Contain)
    }
    function times(n) { return n === 0 ? "∞" : n }

    // ------------------------------------------------ theme (Solarized)
    QtObject {
        id: theme
        readonly property bool dark: win.themeName === "dark"
        readonly property color bg:         dark ? "#002b36" : "#fdf6e3"
        readonly property color surface:    dark ? "#073642" : "#eee8d5"
        readonly property color surfaceAlt: dark ? "#0e4452" : "#e4dcc3"
        readonly property color text:       dark ? "#eee8d5" : "#586e75"
        readonly property color textDim:    dark ? "#839496" : "#657b83"
        readonly property color accent:     "#2aa198"
        readonly property color onAccent:   dark ? "#002b36" : "#fdf6e3"
        readonly property color line:       dark ? "#125463" : "#d6cfb6"
        readonly property color highlight:  "#b58900"
        readonly property color danger:     "#dc322f"
    }

    Settings {
        category: "ui"
        property alias themeName: win.themeName
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
            c.reset(); c.clearRect(0, 0, width, height)
            var s = width / 24
            c.scale(s, s)
            c.fillStyle = color; c.strokeStyle = color
            c.lineWidth = 2; c.lineCap = "round"
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
                width: ib.size * 0.42; height: width
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
        property bool closable: false
        signal closed()
        focusPolicy: Qt.NoFocus
        hoverEnabled: true
        implicitHeight: 32
        leftPadding: 14
        rightPadding: pl.closable ? 10 : 14
        implicitWidth: contentItem.implicitWidth + leftPadding + rightPadding
        contentItem: RowLayout {
            spacing: 8
            Text {
                Layout.alignment: Qt.AlignVCenter
                text: pl.text
                font.pixelSize: 13
                color: pl.active ? pl.t.accent : pl.t.textDim
            }
            Text {
                Layout.alignment: Qt.AlignVCenter
                visible: pl.closable
                text: "✕"
                font.pixelSize: 11
                color: pl.t.textDim
                MouseArea {
                    anchors.fill: parent; anchors.margins: -8
                    cursorShape: Qt.PointingHandCursor
                    onClicked: pl.closed()
                }
            }
        }
        background: Rectangle {
            radius: height / 2
            color: pl.active ? Qt.alpha(pl.t.accent, 0.15) : (pl.hovered ? pl.t.surfaceAlt : "transparent")
            border.width: 1
            border.color: pl.active ? pl.t.accent : pl.t.line
        }
    }

    component Segmented: Rectangle {
        id: sg
        property var t
        property var labels: []
        property int current: 0
        signal picked(int index)
        implicitHeight: 32
        implicitWidth: segRow.implicitWidth + 4
        radius: height / 2
        color: t.surfaceAlt
        Row {
            id: segRow
            anchors.centerIn: parent
            Repeater {
                model: sg.labels
                delegate: Rectangle {
                    required property int index
                    required property string modelData
                    width: lbl.implicitWidth + 28
                    height: 28
                    radius: 14
                    color: index === sg.current ? sg.t.accent : "transparent"
                    Text {
                        id: lbl
                        anchors.centerIn: parent
                        text: modelData
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        color: index === sg.current ? sg.t.onAccent : sg.t.textDim
                    }
                    MouseArea { anchors.fill: parent; onClicked: sg.picked(index) }
                }
            }
        }
    }

    component Track: Slider {
        id: tr
        property var t
        property real markA: -1
        property real markB: -1
        focusPolicy: Qt.NoFocus
        implicitHeight: 20
        background: Rectangle {
            x: tr.leftPadding
            y: tr.topPadding + tr.availableHeight / 2 - height / 2
            width: tr.availableWidth
            height: 4; radius: 2
            color: tr.t.line
            Rectangle {
                width: tr.visualPosition * parent.width
                height: parent.height; radius: 2; color: tr.t.accent
            }
            Rectangle {
                visible: tr.markA >= 0 && tr.markB > tr.markA
                x: tr.markA * parent.width
                width: (tr.markB - tr.markA) * parent.width
                y: -4; height: parent.height + 8; radius: 2
                color: Qt.alpha(tr.t.accent, 0.3)
            }
            Rectangle {
                visible: tr.markA >= 0
                x: tr.markA * parent.width - 1; y: -5
                width: 2; height: 14; color: tr.t.accent
            }
            Rectangle {
                visible: tr.markB >= 0
                x: tr.markB * parent.width - 1; y: -5
                width: 2; height: 14; color: tr.t.accent
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

    component Picker: ComboBox {
        id: pk
        property var t
        property string family: ""
        property string selectedId: ""
        signal chosen(string id)

        function sync() {
            var m = model
            if (!m) return
            for (var i = 0; i < m.length; i++) {
                if (m[i].id === selectedId) { currentIndex = i; return }
            }
        }
        onSelectedIdChanged: sync()
        onModelChanged: sync()
        Component.onCompleted: sync()
        onActivated: function(i) { pk.chosen(pk.model[i].id) }

        implicitHeight: 34
        font.pixelSize: 13
        textRole: "name"
        focusPolicy: Qt.NoFocus

        contentItem: Text {
            leftPadding: 10
            rightPadding: pk.indicator.width + 6
            text: pk.displayText || ""
            font.pixelSize: 13
            font.family: pk.family !== "" ? pk.family : Qt.application.font.family
            color: pk.t.text
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            color: pk.hovered ? pk.t.surfaceAlt : "transparent"
            border.color: pk.t.line
            border.width: 1
            radius: 8
        }
        indicator: Text {
            x: pk.width - width - 8
            y: (pk.height - height) / 2
            text: "▾"
            font.pixelSize: 12
            color: pk.t.textDim
        }
        popup: Popup {
            y: pk.height - 1
            width: pk.width
            implicitHeight: contentItem.implicitHeight + 4
            padding: 2
            background: Rectangle { color: pk.t.surface; border.color: pk.t.line; radius: 8 }
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: pk.popup.visible ? pk.delegateModel : null
                currentIndex: pk.highlightedIndex
                ScrollBar.vertical: ScrollBar { }
            }
        }
        delegate: ItemDelegate {
            width: pk.width
            implicitHeight: 32
            highlighted: pk.highlightedIndex === index
            contentItem: Text {
                leftPadding: 8
                text: modelData.name || ""
                font.pixelSize: 13
                font.family: pk.family !== "" ? pk.family : Qt.application.font.family
                color: pk.t.text
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: parent.highlighted ? Qt.alpha(pk.t.accent, 0.18) : "transparent"
                radius: 6
            }
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
    Shortcut { sequence: "W";           onActivated: player.wordByWord = !player.wordByWord }
    Shortcut { sequence: "L";           onActivated: player.togglePlaylistLoop() }
    Shortcut { sequence: "R";           onActivated: player.cycleAyahRepeat() }
    Shortcut { sequence: "G";           onActivated: player.cycleGroupRepeat() }
    Shortcut { sequence: "H";           onActivated: player.hideText = !player.hideText }
    Shortcut { sequence: "X";           onActivated: player.markMode = !player.markMode }
    Shortcut { sequence: "D";           onActivated: win.themeName = theme.dark ? "light" : "dark" }
    Shortcut { sequence: "P";           onActivated: win.sidebarOpen = !win.sidebarOpen }
    Shortcut { sequences: ["+", "="];   onActivated: win.fontScale = Math.min(1.8, win.fontScale + 0.1) }
    Shortcut { sequence: "-";           onActivated: win.fontScale = Math.max(0.6, win.fontScale - 0.1) }
    Shortcut { sequence: "[";           onActivated: player.markStart() }
    Shortcut { sequence: "]";           onActivated: player.markEnd() }
    Shortcut { sequence: "Escape";      onActivated: player.clearLoop() }

    Binding {
        target: seek
        property: "value"
        value: player.position
        when: !seek.pressed
    }

    Connections {
        target: player
        function onContentReset() {
            fadeIn.restart()
            flick.contentY = 0
            win.focusWord = -1
            win.revealed = ({})
        }
        function onCurrentIndexChanged() {
            if (player.currentIndex >= 0) win.ensureVisible(player.currentIndex)
        }
        function onToast(msg) { toastText.text = msg; toast.opacity = 1; toastTimer.restart() }
    }

    // ------------------------------------------------ popups
    Popup {
        id: settingsPopup
        parent: Overlay.overlay
        anchors.centerIn: Overlay.overlay
        modal: true
        focus: true
        width: 380
        padding: 20
        background: Rectangle { color: theme.surface; radius: 14; border.color: theme.line }
        contentItem: ColumnLayout {
            spacing: 10
            Text { text: "Settings"; font.pixelSize: 18; font.weight: Font.DemiBold; color: theme.text }

            Text { text: "Playlist"; font.pixelSize: 12; color: theme.textDim; Layout.topMargin: 6 }
            Picker {
                t: theme
                Layout.fillWidth: true
                model: player.availablePlaylists
                selectedId: player.currentPlaylistId
                onChosen: function(id) { player.setPlaylist(id) }
            }
            Text { text: "Reciter"; font.pixelSize: 12; color: theme.textDim }
            Picker {
                t: theme
                Layout.fillWidth: true
                model: player.reciterNames
                selectedId: player.currentReciter
                onChosen: function(id) { player.setReciter(id) }
            }
            Text { text: "Translation"; font.pixelSize: 12; color: theme.textDim }
            Picker {
                t: theme
                Layout.fillWidth: true
                family: player.banglaFontFamily
                model: player.translationNames
                selectedId: player.currentTranslation
                onChosen: function(id) { player.setTranslation(id) }
            }
            Text { text: "Theme"; font.pixelSize: 12; color: theme.textDim }
            Segmented {
                t: theme
                labels: ["Solarized Dark", "Solarized Light"]
                current: theme.dark ? 0 : 1
                onPicked: function(i) { win.themeName = i === 0 ? "dark" : "light" }
            }
            Text { text: "Text size"; font.pixelSize: 12; color: theme.textDim }
            RowLayout {
                spacing: 10
                IconButton { t: theme; text: "A−"; onClicked: win.fontScale = Math.max(0.6, win.fontScale - 0.1) }
                Text { text: Math.round(win.fontScale * 100) + "%"; color: theme.text; font.pixelSize: 14
                       Layout.preferredWidth: 48; horizontalAlignment: Text.AlignHCenter }
                IconButton { t: theme; text: "A+"; onClicked: win.fontScale = Math.min(1.8, win.fontScale + 0.1) }
            }
        }
    }

    Popup {
        id: managePopup
        parent: Overlay.overlay
        anchors.centerIn: Overlay.overlay
        modal: true
        focus: true
        width: 380
        padding: 20
        background: Rectangle { color: theme.surface; radius: 14; border.color: theme.line }
        onOpened: addField.forceActiveFocus()
        contentItem: ColumnLayout {
            spacing: 10
            Text { text: "Memorization list"; font.pixelSize: 18; font.weight: Font.DemiBold; color: theme.text }
            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "Add an ayah or range as surah:ayah — for example 2:255, 2:1-5 or 36:1-10."
                font.pixelSize: 12
                color: theme.textDim
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                TextField {
                    id: addField
                    Layout.fillWidth: true
                    placeholderText: "2:255"
                    color: theme.text
                    placeholderTextColor: theme.textDim
                    font.pixelSize: 14
                    selectByMouse: true
                    background: Rectangle { color: theme.bg; radius: 8; border.color: theme.line }
                    onAccepted: if (player.addMemorization(text)) text = ""
                }
                Pill {
                    t: theme; text: "Add"; active: true
                    onClicked: if (player.addMemorization(addField.text)) addField.text = ""
                }
            }
            ListView {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(240, contentHeight)
                clip: true
                model: player.memorizationGroups
                spacing: 2
                ScrollBar.vertical: ScrollBar { }
                delegate: Rectangle {
                    required property var modelData
                    width: ListView.view.width
                    height: 36
                    radius: 8
                    color: theme.surfaceAlt
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 6
                        Text { Layout.fillWidth: true; text: modelData.label; color: theme.text; font.pixelSize: 14 }
                        IconButton { t: theme; size: 28; text: "✕"; tip: "Remove"
                            onClicked: player.removeMemorization(modelData.id) }
                    }
                }
            }
            Text {
                visible: player.memorizationGroups.length === 0
                text: "Nothing yet."
                color: theme.textDim
                font.pixelSize: 13
            }
        }
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
                    spacing: 8

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

                    Segmented {
                        t: theme
                        labels: ["Listen", "Memorize"]
                        current: player.memorizeMode ? 1 : 0
                        enabled: !player.initializing
                        onPicked: function(i) { player.setMode(i === 1 ? "memorize" : "listen") }
                    }
                    Pill {
                        t: theme
                        text: "Translation"
                        active: player.showTranslation
                        onClicked: player.showTranslation = !player.showTranslation
                        ToolTip.visible: hovered; ToolTip.text: "Show/hide translation (T)"; ToolTip.delay: 600
                    }
                    Pill {
                        t: theme
                        text: "Word by word"
                        active: player.wordByWord
                        onClicked: player.wordByWord = !player.wordByWord
                        ToolTip.visible: hovered; ToolTip.text: "Highlight words and see their meaning (W)"; ToolTip.delay: 600
                    }
                    IconButton { t: theme; text: "◐"; tip: "Light / dark (D)"
                        onClicked: win.themeName = theme.dark ? "light" : "dark" }
                    IconButton { t: theme; text: "⚙"; tip: "Settings"
                        onClicked: settingsPopup.open() }
                }
            }

            // ---- reading area
            Flickable {
                id: flick
                anchors { top: topBar.bottom; bottom: tools.top; left: parent.left; right: parent.right }
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
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        visible: player.loopActive
                        text: "Looping · pass " + (player.loopDone + 1)
                              + (player.loopTotal > 0 ? " of " + player.loopTotal : "")
                        font.pixelSize: 13
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

                    // plain Arabic text (Bismillah, duas, or when word data isn't available)
                    Text {
                        Layout.fillWidth: true
                        Layout.topMargin: 8
                        visible: player.words.length === 0 && !player.textHidden
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
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.topMargin: 8
                        visible: player.words.length === 0 && player.textHidden
                        text: "Text hidden — recite from memory"
                        font.pixelSize: 18
                        color: theme.textDim
                    }

                    // Arabic text as words: hover highlights, meaning shows below, mistakes marked in red
                    Flow {
                        id: wordFlow
                        Layout.fillWidth: true
                        Layout.topMargin: 8
                        visible: player.words.length > 0
                        layoutDirection: Qt.RightToLeft
                        spacing: 4

                        Repeater {
                            model: player.words
                            delegate: Rectangle {
                                id: wd
                                required property var modelData
                                readonly property bool concealed: player.textHidden && !win.revealed[modelData.index]
                                readonly property bool focused: win.focusWord === modelData.index
                                radius: 8
                                color: modelData.mistake ? Qt.alpha(theme.danger, 0.18)
                                     : focused ? Qt.alpha(theme.highlight, 0.28)
                                     : wma.containsMouse ? Qt.alpha(theme.highlight, 0.14) : "transparent"
                                border.width: modelData.mistake ? 1 : 0
                                border.color: theme.danger
                                implicitWidth: wt.implicitWidth + 14
                                implicitHeight: wt.implicitHeight + 6

                                Text {
                                    id: wt
                                    anchors.centerIn: parent
                                    text: wd.concealed
                                          ? "•".repeat(Math.max(2, Math.round(wd.modelData.arabic.length / 3)))
                                          : wd.modelData.arabic
                                    font.family: player.fontFamily
                                    font.pixelSize: Math.round(40 * win.fontScale)
                                    color: wd.modelData.mistake ? theme.danger
                                         : wd.concealed ? theme.textDim : theme.text
                                }
                                MouseArea {
                                    id: wma
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                                    cursorShape: Qt.PointingHandCursor
                                    onEntered: if (!wd.concealed) win.focusWord = wd.modelData.index
                                    onClicked: function(m) {
                                        var i = wd.modelData.index
                                        if (player.memorizeMode && (m.button === Qt.RightButton || player.markMode)) {
                                            win.reveal(i)
                                            player.toggleMistake(i)
                                        } else if (wd.concealed) {
                                            win.reveal(i)
                                        } else {
                                            win.focusWord = i
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // meaning bar (fixed height so nothing jumps while hovering)
                    Rectangle {
                        id: meaningBar
                        Layout.fillWidth: true
                        visible: player.wordByWord && player.words.length > 0
                        height: 64
                        radius: 10
                        color: theme.surfaceAlt
                        border.color: theme.line
                        border.width: 1
                        property var w: (win.focusWord >= 0 && win.focusWord < player.words.length)
                                        ? player.words[win.focusWord] : null

                        Text {
                            anchors.centerIn: parent
                            visible: meaningBar.w === null
                            text: "Hover or tap a word to see its meaning"
                            font.pixelSize: 13
                            color: theme.textDim
                        }
                        RowLayout {
                            anchors.centerIn: parent
                            visible: meaningBar.w !== null
                            spacing: 16
                            Text {
                                text: meaningBar.w ? meaningBar.w.arabic : ""
                                font.family: player.fontFamily
                                font.pixelSize: 30
                                color: theme.text
                            }
                            ColumnLayout {
                                spacing: 2
                                Text {
                                    visible: text !== ""
                                    text: meaningBar.w ? meaningBar.w.bangla : ""
                                    font.family: player.banglaFontFamily
                                    font.pixelSize: 16
                                    color: theme.text
                                }
                                Text {
                                    visible: text !== ""
                                    text: meaningBar.w ? meaningBar.w.english : ""
                                    font.pixelSize: 14
                                    color: theme.textDim
                                }
                            }
                        }
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
                        font.family: player.banglaFontFamily
                        lineHeight: 1.4
                        lineHeightMode: Text.ProportionalHeight
                        color: theme.textDim
                    }
                }
            }

            // ---- empty / preparing state
            ColumnLayout {
                anchors.centerIn: flick
                visible: player.currentIndex < 0 && !player.initializing
                spacing: 8
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: (player.memorizeMode && player.totalCount === 0)
                          ? "Your memorization list is empty" : "Preparing your playlist…"
                    font.pixelSize: 20
                    color: theme.text
                }
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: (player.memorizeMode && player.totalCount === 0)
                          ? "Add the ayahs you are memorizing and they will be recited here."
                          : "The first run downloads audio; after that it works offline."
                    font.pixelSize: 14
                    color: theme.textDim
                }
                Pill {
                    Layout.alignment: Qt.AlignHCenter
                    visible: player.memorizeMode && player.totalCount === 0
                    t: theme; text: "＋ Add ayahs"; active: true
                    onClicked: managePopup.open()
                }
            }

            // ---- toast
            Rectangle {
                id: toast
                anchors { horizontalCenter: parent.horizontalCenter; bottom: tools.top; bottomMargin: 8 }
                opacity: 0
                visible: opacity > 0
                radius: 18
                color: theme.dark ? "#eee8d5" : "#073642"
                width: toastText.implicitWidth + 36
                height: 36
                Behavior on opacity { NumberAnimation { duration: 200 } }
                Text {
                    id: toastText
                    anchors.centerIn: parent
                    font.pixelSize: 13
                    color: theme.dark ? "#002b36" : "#fdf6e3"
                }
                Timer { id: toastTimer; interval: 3500; onTriggered: toast.opacity = 0 }
            }

            // ---- tools strip: loop A–B, repeat, memorization practice
            Item {
                id: tools
                implicitHeight: toolsFlow.implicitHeight + 16
                height: implicitHeight
                anchors { left: parent.left; right: parent.right; bottom: transport.top }

                Flow {
                    id: toolsFlow
                    anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter
                              leftMargin: 20; rightMargin: 20 }
                    spacing: 12

                    Row {
                        spacing: 6
                        Text { anchors.verticalCenter: parent.verticalCenter; text: "Loop part"
                               font.pixelSize: 12; color: theme.textDim }
                        Pill {
                            t: theme
                            active: player.loopStart >= 0
                            closable: player.loopStart >= 0
                            text: player.loopStart >= 0 ? "A · " + (player.loopStart / 1000).toFixed(1) + "s" : "Set A"
                            ToolTip.visible: hovered; ToolTip.text: "Mark loop start here ( [ )"; ToolTip.delay: 600
                            onClicked: player.markStart()
                            onClosed: player.clearStart()
                        }
                        Pill {
                            t: theme
                            active: player.loopEnd >= 0
                            closable: player.loopEnd >= 0
                            text: player.loopEnd >= 0 ? "B · " + (player.loopEnd / 1000).toFixed(1) + "s" : "Set B"
                            ToolTip.visible: hovered; ToolTip.text: "Mark loop end here ( ] )"; ToolTip.delay: 600
                            onClicked: player.markEnd()
                            onClosed: player.clearEnd()
                        }
                        Pill {
                            t: theme
                            text: "× " + win.times(player.loopTotal)
                            ToolTip.visible: hovered; ToolTip.text: "Passes for the A–B loop"; ToolTip.delay: 600
                            onClicked: player.cycleLoopCount()
                        }
                    }

                    Row {
                        spacing: 6
                        Text { anchors.verticalCenter: parent.verticalCenter; text: "Repeat"
                               font.pixelSize: 12; color: theme.textDim }
                        Pill {
                            t: theme
                            active: player.ayahRepeat !== 1
                            text: "Ayah × " + win.times(player.ayahRepeat)
                            ToolTip.visible: hovered; ToolTip.text: "Play each ayah N times (R)"; ToolTip.delay: 600
                            onClicked: player.cycleAyahRepeat()
                        }
                        Pill {
                            t: theme
                            active: player.groupRepeat !== 1
                            text: "Group × " + win.times(player.groupRepeat)
                            ToolTip.visible: hovered; ToolTip.text: "Repeat the whole group (e.g. Al Baqarah 1–5) N times (G)"; ToolTip.delay: 600
                            onClicked: player.cycleGroupRepeat()
                        }
                        Pill {
                            t: theme
                            active: player.playlistLoop
                            text: "Playlist ↻"
                            ToolTip.visible: hovered; ToolTip.text: "Start over at the end (L)"; ToolTip.delay: 600
                            onClicked: player.togglePlaylistLoop()
                        }
                    }

                    Row {
                        visible: player.memorizeMode
                        spacing: 6
                        Text { anchors.verticalCenter: parent.verticalCenter; text: "Practice"
                               font.pixelSize: 12; color: theme.textDim }
                        Pill {
                            t: theme
                            active: player.hideText
                            text: "Hide text"
                            ToolTip.visible: hovered; ToolTip.text: "Hide words; click a word to reveal it (H)"; ToolTip.delay: 600
                            onClicked: player.hideText = !player.hideText
                        }
                        Pill {
                            t: theme
                            active: player.markMode
                            text: "Mark mistakes"
                            ToolTip.visible: hovered
                            ToolTip.text: "Click words you got wrong (X). Right-click always marks."
                            ToolTip.delay: 600
                            onClicked: player.markMode = !player.markMode
                        }
                        Pill {
                            t: theme
                            visible: player.mistakeCount > 0
                            text: player.mistakeCount + " marked"
                            closable: true
                            ToolTip.visible: hovered; ToolTip.text: "✕ clears the marks on this ayah"; ToolTip.delay: 600
                            onClosed: player.clearMistakes()
                        }
                    }
                }
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
                            markA: player.duration > 0 && player.loopStart >= 0 ? player.loopStart / player.duration : -1
                            markB: player.duration > 0 && player.loopEnd >= 0 ? player.loopEnd / player.duration : -1
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

                        Item {
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            Layout.fillHeight: true
                            RowLayout {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 8
                                IconButton {
                                    t: theme; size: 36
                                    visible: content.width > 640
                                    iconKind: player.muted || player.volume === 0 ? "muted" : "volume"
                                    tip: "Mute (M)"
                                    onClicked: player.muted = !player.muted
                                }
                                Track {
                                    t: theme
                                    visible: content.width > 640
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
                    spacing: 6

                    // Playlist picker in listen mode
                    Picker {
                        t: theme
                        Layout.fillWidth: true
                        visible: !player.memorizeMode
                        model: player.availablePlaylists
                        selectedId: player.currentPlaylistId
                        onChosen: function(id) { player.setPlaylist(id) }
                    }
                    // Title in memorize mode
                    Text {
                        Layout.fillWidth: true
                        visible: player.memorizeMode
                        text: "Memorization"
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                        color: theme.text
                    }

                    IconButton { t: theme; size: 36; text: "＋"; tip: "Add / manage ayahs"
                        visible: player.memorizeMode
                        onClicked: managePopup.open() }
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
                    section.labelPositioning: ViewSection.InlineLabels
                    section.delegate: Item {
                        required property string section
                        width: list.width
                        height: 40
                        Text {
                            anchors { left: parent.left; leftMargin: 16; right: parent.right
                                      rightMargin: 16; bottom: parent.bottom; bottomMargin: 6 }
                            text: parent.section
                            elide: Text.ElideRight
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                            font.letterSpacing: 0.5
                            color: theme.accent
                        }
                    }

                    delegate: ItemDelegate {
                        id: row
                        required property int index
                        required property string label
                        required property string status
                        required property string errorText
                        required property int ayahNo
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
                            Rectangle {
                                visible: row.ayahNo > 0
                                Layout.preferredWidth: 30
                                Layout.preferredHeight: 22
                                radius: 11
                                color: row.highlighted ? theme.accent : theme.surfaceAlt
                                Text {
                                    anchors.centerIn: parent
                                    text: row.ayahNo
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                    color: row.highlighted ? theme.onAccent : theme.textDim
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
                            Text { visible: row.status === "loading"; text: "…"; color: theme.textDim }
                            Text { visible: row.status === "error"; text: "⚠"; color: theme.danger }
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

        // ============ initialization overlay ============
        Rectangle {
            id: initOverlay
            anchors.fill: parent
            z: 100
            color: Qt.alpha(theme.bg, 0.96)
            visible: player.initializing

            MouseArea { anchors.fill: parent }

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 20

                Item {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: 72
                    Layout.preferredHeight: 72

                    Canvas {
                        id: spinnerCanvas
                        anchors.fill: parent
                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.reset(); ctx.clearRect(0, 0, width, height)
                            var cx = width / 2, cy = height / 2, r = width / 2 - 6
                            ctx.strokeStyle = theme.line; ctx.lineWidth = 5
                            ctx.beginPath(); ctx.arc(cx, cy, r, 0, 2 * Math.PI); ctx.stroke()
                            ctx.strokeStyle = theme.accent; ctx.lineWidth = 5; ctx.lineCap = "round"
                            ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI / 2); ctx.stroke()
                        }
                    }
                    RotationAnimator on rotation {
                        from: 0; to: 360; duration: 900
                        loops: Animation.Infinite
                        running: player.initializing
                    }
                }
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Preparing Ruqya Quran"
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                    color: theme.text
                }
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    visible: player.initMessage !== ""
                    text: player.initMessage
                    font.pixelSize: 13
                    color: theme.textDim
                    elide: Text.ElideRight
                    Layout.maximumWidth: 420
                }
                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: 340
                    Layout.preferredHeight: 4
                    radius: 2
                    color: theme.line
                    visible: player.initTotal > 0
                    Rectangle {
                        width: player.initTotal > 0
                               ? parent.width * Math.min(1, player.initCurrent / player.initTotal) : 0
                        height: parent.height; radius: 2; color: theme.accent
                        Behavior on width { NumberAnimation { duration: 200 } }
                    }
                }
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    visible: player.initTotal > 0
                    text: player.initCurrent + " / " + player.initTotal
                    font.pixelSize: 12
                    color: theme.textDim
                }
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.topMargin: 12
                    visible: player.initTotal > 0
                    text: "Downloads happen once; after that it works offline."
                    font.pixelSize: 11
                    color: theme.textDim
                    opacity: 0.6
                }
            }
        }
    }
}