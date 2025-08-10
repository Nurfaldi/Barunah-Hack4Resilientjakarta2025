import React, { useState, useEffect, useRef } from 'react';

// --- Icon Components ---
const UserIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6">
        <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path>
        <circle cx="12" cy="7" r="4"></circle>
    </svg>
);

const BotIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6">
        <path d="M12 8V4H8"></path>
        <rect width="16" height="12" x="4" y="8" rx="2"></rect>
        <path d="M2 14h2"></path>
        <path d="M20 14h2"></path>
        <path d="M15 13v2"></path>
        <path d="M9 13v2"></path>
    </svg>
);

// --- Survey Questions Configuration ---
const questions = [
    { id: 'nama', category: 'Identifier', questionText: 'Halo! Sebelum mulai, boleh perkenalkan, siapa nama Anda?', answerType: 'text' },
    { id: 'usia', category: 'Identifier', questionText: 'Berapa usia Anda saat ini?', answerType: 'dropdown', options: ['Di bawah 17', '17-25', '26-35', '36-45', '46-55', 'Di atas 55'] },
    { id: 'pekerjaan', category: 'Identifier', questionText: 'Apa pekerjaan utama Anda?', answerType: 'dropdown-isian', options: ['Pelajar/Mahasiswa', 'Karyawan Swasta', 'Wiraswasta', 'Ibu Rumah Tangga', 'Pekerja Lepas', 'Tidak Bekerja', 'Lainnya'] },
    { id: 'asalWilayah', category: 'Identifier', questionText: 'Anda berasal dari wilayah atau kampung mana di Jakarta?', answerType: 'text' },
    { id: 'lamaTinggal', category: 'Identifier', questionText: 'Sudah berapa lama Anda tinggal di sana?', answerType: 'dropdown', options: ['Kurang dari 1 tahun', '1-5 tahun', '6-10 tahun', '11-20 tahun', 'Lebih dari 20 tahun'] },
    // Flood Level
    { id: 'seringBanjir', category: 'Flood Level', questionText: 'Seberapa sering wilayah Anda mengalami banjir?', answerType: 'radio', options: ['Lebih dari sekali dalam setahun', 'Setahun sekali', 'Dua tahun sekali', 'Lebih dari dua tahun sekali', 'Tidak pernah'] },
    { id: 'durasiBanjir', category: 'Flood Level', questionText: 'Jika terjadi banjir, biasanya berapa lama durasinya?', answerType: 'radio', options: ['Kurang dari sehari', 'Sehari penuh', '2-3 hari', '3-5 hari', 'Lebih dari 5 hari', 'Tidak relevan'] },
    { id: 'banjirTerakhir', category: 'Flood Level', questionText: 'Kapan terakhir kali Anda mengalami banjir? (Bulan dan Tahun, contoh: Januari 2024)', answerType: 'text' },
    { id: 'ketinggianBanjir', category: 'Flood Level', questionText: 'Kira-kira, berapa ketinggian maksimal banjir yang terakhir Anda alami?', answerType: 'radio', options: ['Kurang dari 30cm (di bawah lutut)', '30-60cm (selutut)', '60cm - 1 meter (sepaha/sepinggang)', '1-2 meter (sedada)', 'Lebih dari 2 meter (di atas kepala)'] },
    // Economic
    { id: 'pengeluaranKeluarga', category: 'Economic', questionText: 'Berapa rata-rata pengeluaran keluarga Anda dalam sebulan?', answerType: 'radio', options: ['Kurang dari Rp 1 juta', 'Rp 1 juta - Rp 2 juta', 'Rp 2 juta - Rp 3.5 juta', 'Rp 3.5 juta - Rp 5 juta', 'Di atas Rp 5 juta'] },
    { id: 'jumlahTanggungan', category: 'Economic', questionText: 'Berapa jumlah anggota keluarga yang menjadi tanggungan Anda (termasuk Anda sendiri)?', answerType: 'radio', options: ['1 (sendiri)', '2', '3', '4', '5', '6', 'Lebih dari 6'] },
    { id: 'transportasi', category: 'Economic', questionText: 'Untuk bepergian sehari-hari, moda transportasi apa yang paling sering Anda gunakan?', answerType: 'radio', options: ['Lebih banyak di rumah saja', 'Berjalan kaki', 'Sepeda', 'Sepeda motor pribadi', 'Mobil pribadi', 'Ojek/ojek online', 'Taksi/taksi online', 'Kendaraan umum (TransJakarta, KRL, Angkot)'] },
    { id: 'tujuanBepergian', category: 'Economic', questionText: 'Ke mana biasanya tujuan perjalanan rutin Anda?', answerType: 'dropdown-isian', options: ['Tempat Kerja', 'Pasar', 'Sekolah/Kampus', 'Lainnya'] },
    { id: 'jarakKerja', category: 'Economic', questionText: 'Berapa jarak dari rumah ke tempat kerja/aktivitas utama Anda?', answerType: 'radio', options: ['Kurang dari 1 km', '1-2 km', '2-5 km', '5-10 km', 'Lebih dari 10 km', 'Tidak relevan'] },
    // Social
    { id: 'kenyamananTinggal', category: 'Social', questionText: 'Seberapa nyaman Anda tinggal di wilayah Anda saat ini? Beri nilai dari 1 (sangat tidak nyaman) hingga 10 (sangat nyaman).', answerType: 'likert', options: Array.from({ length: 10 }, (_, i) => i + 1) },
    { id: 'kenalTetangga', category: 'Social', questionText: 'Berapa banyak tetangga di sekitar yang Anda kenal (sekadar tahu nama atau wajah)?', answerType: 'radio', options: ['Hampir tidak ada', '1-5 orang', '6-10 orang', '11-20 orang', 'Lebih dari 20 orang'] },
    { id: 'kenalDekatTetangga', category: 'Social', questionText: 'Dari yang Anda kenal, berapa banyak tetangga yang Anda kenal dekat (bisa saling bantu atau mengobrol santai)?', answerType: 'radio', options: ['Tidak ada yang dekat', '1-3 orang', '4-6 orang', '7-10 orang', 'Lebih dari 10 orang'] },
    { id: 'kemungkinanPindah', category: 'Social', questionText: 'Jika ada kesempatan dan kemampuan, seberapa besar kemungkinan Anda akan pindah ke wilayah lain di Jabodetabek? Beri nilai dari 1 (sangat tidak mungkin) hingga 10 (sangat mungkin).', answerType: 'likert', options: Array.from({ length: 10 }, (_, i) => i + 1) },
    { id: 'kesanWilayah', category: 'Social', questionText: 'Terakhir, bisa ceritakan sedikit kesan atau pandangan Anda tentang kampung/wilayah Anda?', answerType: 'textarea' },
];

// --- Main App Component ---
export default function App() {
    const [messages, setMessages] = useState([]);
    const [answers, setAnswers] = useState({});
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [isFinished, setIsFinished] = useState(false);
    const [userInput, setUserInput] = useState('');
    const [otherSpecify, setOtherSpecify] = useState('');
    const chatEndRef = useRef(null);

    // Effect to start the conversation
    useEffect(() => {
        setMessages([{ sender: 'bot', text: questions[0].questionText }]);
    }, []);

    // Effect to scroll to the bottom of the chat
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleInputChange = (e) => {
        setUserInput(e.target.value);
    };

    const handleOtherSpecifyChange = (e) => {
        setOtherSpecify(e.target.value);
    };

    const processAnswer = (answer) => {
        const currentQuestion = questions[currentQuestionIndex];
        let finalAnswer = answer;

        // Handle 'Lainnya' input
        if (currentQuestion.answerType === 'dropdown-isian' && answer === 'Lainnya') {
            finalAnswer = `Lainnya: ${otherSpecify}`;
        }
         if (currentQuestion.answerType === 'radio' && answer.startsWith('Lainnya:')) {
            finalAnswer = answer;
        }


        // Save the answer
        setAnswers(prev => ({ ...prev, [currentQuestion.id]: finalAnswer }));

        // Add user message to chat
        setMessages(prev => [...prev, { sender: 'user', text: finalAnswer }]);

        // Move to the next question or finish
        const nextIndex = currentQuestionIndex + 1;
        if (nextIndex < questions.length) {
            setCurrentQuestionIndex(nextIndex);
            setMessages(prev => [...prev, { sender: 'bot', text: questions[nextIndex].questionText }]);
        } else {
            setIsFinished(true);
            setMessages(prev => [...prev, { sender: 'bot', text: 'Terima kasih banyak atas partisipasi Anda! Kontribusi Anda sangat berharga. Berikut adalah ringkasan jawaban Anda.' }]);
        }

        // Reset inputs
        setUserInput('');
        setOtherSpecify('');
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (userInput.trim() === '') return;
        processAnswer(userInput);
    };

    const handleOptionClick = (option) => {
        if ( (questions[currentQuestionIndex].answerType === 'dropdown-isian' || questions[currentQuestionIndex].answerType === 'radio') && option === 'Lainnya' ) {
             setUserInput(option); // Keep track of the selection
             return; // Don't process yet, wait for text input
        }
        processAnswer(option);
    };
    
    const handleOtherSubmit = (e) => {
        e.preventDefault();
        if (otherSpecify.trim() === '') return;
        processAnswer(`Lainnya: ${otherSpecify}`);
    }


    const restartSurvey = () => {
        setMessages([{ sender: 'bot', text: questions[0].questionText }]);
        setAnswers({});
        setCurrentQuestionIndex(0);
        setIsFinished(false);
        setUserInput('');
        setOtherSpecify('');
    };

    // --- Render Functions ---
    const renderInput = () => {
        if (isFinished) return null;

        const currentQuestion = questions[currentQuestionIndex];

        switch (currentQuestion.answerType) {
            case 'text':
            case 'textarea':
                return (
                    <form onSubmit={handleSubmit} className="flex items-center space-x-2">
                        <input
                            type="text"
                            value={userInput}
                            onChange={handleInputChange}
                            className="flex-grow p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition"
                            placeholder="Ketik jawaban Anda..."
                        />
                        <button type="submit" className="bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700 transition shadow">
                            Kirim
                        </button>
                    </form>
                );
            
            case 'radio':
            case 'dropdown':
                 if (userInput === 'Lainnya' && currentQuestion.options.includes('Lainnya')) {
                    return (
                        <form onSubmit={handleOtherSubmit} className="flex items-center space-x-2">
                            <input
                                type="text"
                                value={otherSpecify}
                                onChange={handleOtherSpecifyChange}
                                className="flex-grow p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition"
                                placeholder="Sebutkan lainnya..."
                                autoFocus
                            />
                            <button type="submit" className="bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700 transition shadow">
                                Kirim
                            </button>
                        </form>
                    );
                }
                return (
                    <div className="flex flex-wrap gap-2 justify-center">
                        {currentQuestion.options.map(option => (
                            <button key={option} onClick={() => handleOptionClick(option)} className="bg-white border border-blue-500 text-blue-600 px-4 py-2 rounded-full hover:bg-blue-100 transition shadow-sm">
                                {option}
                            </button>
                        ))}
                    </div>
                );

            case 'dropdown-isian':
                if (userInput === 'Lainnya') {
                    return (
                        <form onSubmit={handleOtherSubmit} className="flex items-center space-x-2">
                            <input
                                type="text"
                                value={otherSpecify}
                                onChange={handleOtherSpecifyChange}
                                className="flex-grow p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition"
                                placeholder="Sebutkan lainnya..."
                                autoFocus
                            />
                            <button type="submit" className="bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700 transition shadow">
                                Kirim
                            </button>
                        </form>
                    );
                }
                return (
                     <div className="flex flex-wrap gap-2 justify-center">
                        {currentQuestion.options.map(option => (
                            <button key={option} onClick={() => handleOptionClick(option)} className="bg-white border border-blue-500 text-blue-600 px-4 py-2 rounded-full hover:bg-blue-100 transition shadow-sm">
                                {option}
                            </button>
                        ))}
                    </div>
                );

            case 'likert':
                return (
                    <div className="flex flex-wrap gap-2 justify-center bg-gray-100 p-3 rounded-lg">
                        {currentQuestion.options.map(option => (
                            <button key={option} onClick={() => handleOptionClick(option)} className="w-10 h-10 flex items-center justify-center bg-white border border-blue-500 text-blue-600 rounded-full hover:bg-blue-100 transition shadow-sm font-semibold">
                                {option}
                            </button>
                        ))}
                    </div>
                );

            default:
                return null;
        }
    };

    return (
        <div className="flex flex-col h-screen bg-gray-50 font-sans">
            <header className="bg-white shadow-md p-4 text-center">
                <h1 className="text-2xl font-bold text-gray-800">Survei Partisipatif Kampung Kota</h1>
                <p className="text-sm text-gray-500">Demi keberlanjutan kampung kota Jakarta</p>
            </header>

            <main className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8">
                <div className="max-w-2xl mx-auto space-y-4">
                    {messages.map((msg, index) => (
                        <div key={index} className={`flex items-start gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                            {msg.sender === 'bot' && <div className="flex-shrink-0 bg-blue-500 text-white rounded-full p-2"><BotIcon /></div>}
                            <div className={`max-w-md p-3 rounded-2xl ${msg.sender === 'user' ? 'bg-blue-600 text-white rounded-br-none' : 'bg-white text-gray-800 rounded-bl-none border'}`}>
                                <p className="text-sm">{msg.text}</p>
                            </div>
                             {msg.sender === 'user' && <div className="flex-shrink-0 bg-gray-300 text-gray-700 rounded-full p-2"><UserIcon /></div>}
                        </div>
                    ))}
                    {isFinished && (
                        <div className="bg-white p-4 rounded-lg shadow-md mt-6">
                            <h2 className="text-lg font-semibold mb-2 text-gray-800">Hasil Survei (JSON)</h2>
                            <pre className="bg-gray-900 text-green-300 p-4 rounded-md text-xs overflow-x-auto">
                                {JSON.stringify(answers, null, 2)}
                            </pre>
                            <button onClick={restartSurvey} className="mt-4 w-full bg-green-600 text-white p-3 rounded-lg hover:bg-green-700 transition shadow">
                                Ulangi Survei
                            </button>
                        </div>
                    )}
                    <div ref={chatEndRef} />
                </div>
            </main>

            <footer className="bg-white p-4 border-t">
                <div className="max-w-2xl mx-auto">
                    {renderInput()}
                </div>
            </footer>
        </div>
    );
}
