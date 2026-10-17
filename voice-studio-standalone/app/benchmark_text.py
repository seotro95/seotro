"""Fixed spoken samples; benchmark jobs never replace the user's script."""

VIETNAMESE = """Buổi sáng bắt đầu bằng ánh nắng dịu dàng xuyên qua khung cửa. Người kể chuyện mở cuốn sổ nhỏ, ghi lại những điều đã học được sau một ngày làm việc. Một câu chuyện hay không cần quá nhiều lời hoa mỹ, nhưng cần có chi tiết rõ ràng và cảm xúc chân thành.

Ở khu chợ đầu làng, tiếng nói cười hòa cùng bước chân của những người đi mua thức ăn. Bà bán hàng lựa từng bó rau tươi, còn bác thợ mộc dừng xe để hỏi thăm người bạn cũ. Nhịp sống bình thường ấy mang đến cảm giác gần gũi mà đôi khi chúng ta dễ bỏ qua.

Khi chuẩn bị một bài đọc dài, hãy kiểm tra tên riêng, con số và những đoạn chuyển ý. Giọng nói nên có nhịp nghỉ vừa phải để người nghe hiểu được nội dung. Bạn có thể sửa từng câu, nghe thử một đoạn ngắn rồi tiếp tục với phần còn lại.

Chiều xuống, con đường ven sông trở nên yên tĩnh hơn. Một nhóm học sinh đi qua cây cầu, bàn về cuốn sách vừa đọc trong lớp. Mỗi người có một cách nhìn khác nhau, nhưng tất cả đều chăm chú lắng nghe để hiểu suy nghĩ của bạn mình.

Đây là phần cuối của bài đo tốc độ. Chương trình cần tạo âm thanh thật từ toàn bộ lời đọc và ghi lại thời gian xử lý trên máy hiện tại. Kết quả của một đoạn thử giúp chọn cấu hình phù hợp, nhưng không thay thế phép đo với một bản thu dài hoàn chỉnh."""

ENGLISH = """A clear voice begins with a clear message. Before recording a long story, read the script carefully and check names, numbers, and transitions between ideas. A short sample can reveal whether the selected voice fits the material and whether the pace feels comfortable.

On a quiet morning, a small group of friends met near the river to plan their next project. Each person brought a different idea, and they took time to listen before deciding what to do. Their conversation showed how patience and careful attention can turn a simple plan into a useful result.

This sample measures the time needed to generate real speech on the current computer. The program must keep every sentence, produce a playable recording, and report the elapsed processing time. The result is a measurement of this sample, while a complete hour of audio requires its own verification."""

SAMPLE_TEXTS = {
    'vi': VIETNAMESE,
    'en-US': ENGLISH, 'en-GB': ENGLISH,
    'ja': '朝の光が窓から差し込むと、町は少しずつ動き始めます。物語を読む前に、名前や数字を確認し、聞き取りやすい速さを選びましょう。短い録音を確認すると、声の特徴や文章の流れが分かります。今日の測定では、入力された文章を省略せず、実際の音声を作ります。処理時間はコンピューターによって変わるため、この結果だけで長い録音の速度を保証することはできません。',
    'ko': '아침 햇살이 창문으로 들어오면 마을은 천천히 하루를 시작합니다. 긴 이야기를 읽기 전에 이름과 숫자를 확인하고 듣기 편한 속도를 선택하세요. 짧은 녹음을 먼저 들으면 목소리의 특징과 문장의 흐름을 알 수 있습니다. 이번 측정은 입력한 문장을 생략하지 않고 실제 음성을 만드는 시간을 기록합니다. 처리 속도는 컴퓨터와 모델에 따라 달라지므로 긴 녹음은 따로 확인해야 합니다.',
    'zh': '清晨的阳光透过窗户，小镇慢慢开始了新的一天。朗读长篇故事之前，请先检查人名、数字和段落之间的联系，再选择舒适的语速。先听一段简短的录音，可以帮助你判断声音是否适合内容。这次测试会保留全部文字，生成真实的声音，并记录当前电脑的处理时间。短样本的结果可以帮助选择设置，但不能保证所有电脑和长篇录音都达到同样的速度。',
    'fr': 'Une voix claire commence par un texte précis. Avant de lire une longue histoire, vérifiez les noms, les nombres et les transitions. Écoutez un court enregistrement pour choisir un rythme agréable. Le programme mesure ici le temps nécessaire pour produire une vraie voix sur cet ordinateur. Toutes les phrases doivent être conservées. Le résultat concerne cet échantillon et ne garantit pas la vitesse de chaque enregistrement long.',
    'de': 'Eine klare Stimme beginnt mit einem verständlichen Text. Prüfen Sie vor einer langen Aufnahme alle Namen, Zahlen und Übergänge. Eine kurze Probe hilft dabei, die passende Stimme und ein angenehmes Tempo zu wählen. Das Programm erzeugt echte Sprache und misst die benötigte Zeit auf diesem Computer. Alle Sätze bleiben erhalten. Die Messung gilt für diese Probe und ist keine Garantie für die Geschwindigkeit jeder langen Aufnahme.',
    'es': 'Una voz clara comienza con un mensaje bien escrito. Antes de grabar una historia larga, revisa los nombres, los números y las transiciones. Una muestra breve ayuda a elegir la voz y un ritmo cómodo. El programa genera audio real y registra el tiempo de procesamiento de este equipo. Todas las frases deben conservarse. Este resultado corresponde a la muestra y no garantiza la misma velocidad para cualquier grabación larga.',
    'it': 'Una voce chiara comincia da un testo preciso. Prima di registrare una storia lunga, controlla i nomi, i numeri e i passaggi tra le idee. Ascoltare un breve esempio aiuta a scegliere la voce e un ritmo piacevole. Il programma crea un audio reale e misura il tempo necessario su questo computer. Ogni frase deve essere conservata. Il risultato descrive questo esempio e non garantisce la stessa velocità per ogni registrazione lunga.',
    'pt': 'Uma voz clara começa com um texto bem escrito. Antes de gravar uma história longa, verifique os nomes, os números e as transições. Uma amostra curta ajuda a escolher a voz e um ritmo confortável. O programa cria áudio real e mede o tempo de processamento neste computador. Todas as frases devem ser mantidas. O resultado descreve esta amostra e não garante a mesma velocidade para qualquer gravação longa.',
    'ru': 'Понятная речь начинается с хорошо подготовленного текста. Перед записью длинного рассказа проверьте имена, числа и переходы между мыслями. Короткий образец помогает выбрать голос и удобный темп. Программа создаёт настоящий звук и измеряет время обработки на этом компьютере. Все предложения должны сохраняться. Этот результат относится к образцу и не гарантирует такую же скорость для любой длинной записи.',
}
