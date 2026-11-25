/* ============================================================
   Переключение языков: RU / KK / EN.
   Русские тексты — в разметке (data-i); при загрузке они
   собираются в словарь, казахский и английский лежат здесь.
   Выбор запоминается в localStorage.
   ============================================================ */
(function () {
  const WA_PHONE = '77066183101';

  const WA_MSG = {
    ru: `Здравствуйте, Шехерезада! Хочу обсудить свою ситуацию.`,
    kk: `Сәлеметсіз бе, Шехерезада! Өз жағдайымды талқылағым келеді.`,
    en: `Hello Shekherezada! I would like to discuss my situation.`,
  };

  const META = {
    ru: {
      title: `Шехерезада Куралбек: юрист, судебные споры и цифровое право | Алматы, Шымкент`,
      desc: `Юрист Шехерезада Куралбек. Судебные споры, цифровые активы, персональные данные, антифрод, корпоративное сопровождение, OSINT. Алматы, Шымкент и дистанционно по Казахстану.`,
    },
    kk: {
      title: `Шехерезада Құралбек: заңгер, сот даулары және цифрлық құқық | Алматы, Шымкент`,
      desc: `Заңгер Шехерезада Құралбек. Сот даулары, цифрлық активтер, дербес деректер, антифрод, корпоративтік сүйемелдеу, OSINT. Алматы, Шымкент және бүкіл Қазақстан бойынша қашықтан.`,
    },
    en: {
      title: `Shekherezada Kuralbek — Lawyer: Litigation & Digital Law | Almaty, Shymkent`,
      desc: `Lawyer Shekherezada Kuralbek. Litigation, digital assets, personal data, anti-fraud, corporate support, OSINT. Almaty, Shymkent and remotely across Kazakhstan.`,
    },
  };

  const I18N = {
    kk: {
      'nav.about': `Мен туралы`,
      'nav.services': `Бағыттар`,
      'nav.why': `Неге мен`,
      'nav.contacts': `Байланыс`,
      'nav.call': `Қоңырау шалу`,
      'nav.wa': `WhatsApp-қа жазу`,

      'hero.eyebrow': `Заңгер · Алматы және Шымкент`,
      'hero.title': `Сот даулары<br><em>және цифрлық құқық</em>`,
      'hero.sub': `Соттарда мүдделерді қорғаймын, цифрлық активтермен, дербес деректермен және антифродпен жұмыс істеймін, бизнесті сүйемелдеймін. Істер бойынша жұмыста OSINT қолданамын.`,
      'hero.cta1': `Кейсіңізді талқылау`,
      'hero.s1n': `2`, 'hero.s1l': `кеңсе: Алматы және Шымкент`,
      'hero.s2n': `Бүкіл ҚР`, 'hero.s2l': `істерді қашықтан жүргіземін`,
      'hero.s3n': `100%`, 'hero.s3l': `жеке әрі құпия`,
      'hero.hint': `Парақтаңыз`,

      'ab.eyebrow': `Мен туралы`,
      'ab.title': `Заңгер.<br><em>OSINT, соттар, цифрлық құқық</em>`,
      'ab.p1': `Менің атым — Құралбек Шехерезада Жан-Айдарқызы. Мен заңгермін, Алматы мен Шымкентте кеңселері бар ZAN PROTECT заң компаниясының тең құрылтайшысы әрі бас директорымын.`,
      'ab.p2': `Негізгі мамандануым — сот даулары. Сонымен қатар цифрлық құқықпен және корпоративтік сүйемелдеумен айналысамын. Істер бойынша жұмыста OSINT — ашық дереккөздер барлауын қолданамын.`,
      'ab.p3': `Мәскеуде оқыдым: қылмыстық-құқықтық бейін бойынша бакалавриат және ұлттық қауіпсіздікті құқықтық қамтамасыз ету бойынша магистратура. Қазақстанда практика жүргіземін.`,
      'ab.p4': `Құқықтық сауаттылықты арттырумен белсенді айналысамын: университеттерде, кәсіпкерлер мен мемлекеттік қызметшілер алдында сөз сөйлеймін, білім беру контентін жүргіземін.`,
      'ab.btn': `Немен айналысамын`,
      'ab.phrole': `Заңгер · Сот даулары және цифрлық құқық`,

      'sv.eyebrow': `Бағыттар`,
      'sv.title': `Немен<br><em>көмектесе аламын</em>`,
      'sv.ask': `Сұрақ қою`,
      'sv.cta': `Талқылау`,
      'sv.c1name': `Сот даулары`,
      'sv.c1body': `
          <p class="svc-desc">Бүкіл Қазақстан бойынша соттарда мүдделерді қорғаймын — наразылықтан шешімге дейін.</p>
          <ul class="svc-list">
            <li>Мүліктік даулар</li>
            <li>Қарыздар мен шығындарды өндіріп алу</li>
            <li>Корпоративтік даулар</li>
            <li>Шетелдік қатысушылармен трансшекаралық даулар</li>
            <li>ҚР ӘРПК бойынша мемлекеттік органдармен даулар</li>
          </ul>`,
      'sv.c2name': `Цифрлық құқық`,
      'sv.c2body': `
          <ul class="svc-list">
            <li><b>Цифрлық қылмыстар:</b> құқықтық бағалау, арыздар, іс бойынша сүйемелдеу</li>
            <li><b>Цифрлық активтер:</b> криптовалюта, P2P-мәмілелер, даулар және қаражатты қайтару</li>
            <li><b>Дербес деректер:</b> заңсыз тарату, бизнеске қойылатын талаптар</li>
            <li><b>Антифрод:</b> шоттар мен карталарды бұғаттау, шектеулерді алып тастау</li>
          </ul>`,
      'sv.c3name': `Корпоративтік сүйемелдеу`,
      'sv.c3body': `
          <p class="svc-desc">Шарттар, наразылық жұмысы, ЖШС мен ЖК-дегі өзгерістер, IT-компанияларды сүйемелдеу, абоненттік қызмет көрсету.</p>`,
      'sv.c4body': `
          <p class="svc-desc">Ашық дереккөздер барлауы. Оны клиенттердің істері бойынша жұмыста қолданамын. Тек заңды әдістер.</p>
          <div class="svc-sub">Жеке клиенттерге</div>
          <ul class="svc-list">
            <li>Мәміле алдында адамды, сатушыны немесе мердігерді тексеру</li>
            <li>Борышкерді және оның мүлкін іздеу</li>
            <li>Сотқа дәлелдер жинау</li>
          </ul>
          <div class="svc-sub">Бизнеске</div>
          <ul class="svc-list">
            <li>Шартқа қол қояр алдында контрагенттер мен серіктестерді тексеру</li>
            <li>Өндіріп алу алдында борышкердің активтерін іздеу</li>
            <li>Компания мен басшылардың цифрлық ізін аудиттеу</li>
          </ul>`,

      'pr.eyebrow': `Қалай жұмыс істеймін`,
      'pr.title': `Жұмыс<br><em>тәртібі</em>`,
      'pr.s1t': `Зерттеу`,
      'pr.s1x': `Сіз жағдайды айтып, құжаттарды жібересіз. Іс бойынша бар мәліметтің бәрін зерттеймін.`,
      'pr.s2t': `Талдау`,
      'pr.s2x': `Фактілерді, дәлелдерді, мерзімдерді және ұстанымның осал тұстарын тексеремін.`,
      'pr.s3t': `Саралау`,
      'pr.s3x': `Бұл заң тұрғысынан не екенін және қандай нормалар қолданылатынын анықтаймын.`,
      'pr.s4t': `Нұсқалар`,
      'pr.s4x': `Оқиғаның ықтимал даму сценарийлерін және әрқайсысының тәуекелдерін түсіндіремін.`,
      'pr.s5t': `Жұмыс`,
      'pr.s5x': `Тек осыдан кейін ғана істі жұмысқа аламын.`,

      'why.eyebrow': `Неге мен`,
      'why.title': `Нені<br><em>білу маңызды</em>`,
      'why.i1t': `Іс бойынша жұмыста OSINT`,
      'why.i1x': `Ашық дереккөздер барлауын қолданамын: ақпарат тауып, оны сот үшін дәлелге айналдырамын.`,
      'why.i2t': `Бүкіл Қазақстан бойынша жұмыс істеймін`,
      'why.i2x': `Кеңселер Алматы мен Шымкентте. Басқа қалалардағы соттарды қашықтан жүргіземін.`,
      'why.i3t': `ZAN PROTECT командасы`,
      'why.i3x': `Сот, корпоративтік және цифрлық мәселелер бойынша заңгерлер.`,
      'why.i4t': `Құқықтық сауаттылықты арттырамын`,
      'why.i4x': `ҚазҰУ мен Қонаев университетінде сөз сөйлеймін, кәсіпкерлер мен мемлекеттік қызметшілерге дәрістер оқимын.`,
      'why.i5t': `Құпиялылық`,
      'why.i5x': `Бәрі жеке әрі құпия.`,

      'cta.eyebrow': `Байланысу`,
      'cta.title': `Кейсіңізді<br><em>талқылайық</em>`,
      'cta.sub': `WhatsApp-қа немесе Direct-ке жазыңыз. Жағдайды сипаттап, құжаттарды қоса беріңіз.`,

      'ct.desc': `Заңгер. Сот даулары және цифрлық құқық. Кеңселер Алматы мен Шымкентте, бүкіл Қазақстан бойынша қашықтан.`,
      'ct.colC': `Байланыс`,
      'ct.colH': `Жұмыс кестесі`,
      'ct.cities': `Алматы және Шымкент · бүкіл ҚР бойынша қашықтан`,
      'ct.h1': `Дс–Жм: 9:00–19:00`,
      'ct.h2': `Сб: 10:00–15:00`,

      'ft.l1': `Құралбек Шехерезада Жан-Айдарқызы. Заңгер. Сот даулары және цифрлық құқық. ZAN PROTECT тең құрылтайшысы.`,
      'ft.l2': `© 2026 Құралбек Шехерезада Жан-Айдарқызы. Барлық құқықтар қорғалған.`,
      'ft.privacy': `Құпиялылық саясаты`,
      'ft.terms': `Сайтты пайдалану шарттары`,
    },

    en: {
      'nav.about': `About`,
      'nav.services': `Practice areas`,
      'nav.why': `Why me`,
      'nav.contacts': `Contacts`,
      'nav.call': `Call`,
      'nav.wa': `Message on WhatsApp`,

      'hero.eyebrow': `Lawyer · Almaty & Shymkent`,
      'hero.title': `Litigation<br><em>and digital law</em>`,
      'hero.sub': `I represent clients in court, work with digital assets, personal data and anti-fraud, and support businesses. I use OSINT in my casework.`,
      'hero.cta1': `Discuss your case`,
      'hero.s1n': `2`, 'hero.s1l': `offices: Almaty & Shymkent`,
      'hero.s2n': `All KZ`, 'hero.s2l': `cases handled remotely`,
      'hero.s3n': `100%`, 'hero.s3l': `private & confidential`,
      'hero.hint': `Scroll`,

      'ab.eyebrow': `About me`,
      'ab.title': `Lawyer.<br><em>OSINT, litigation, digital law</em>`,
      'ab.p1': `My name is Kuralbek Shekherezada Zhan-Aidarkyzy. I am a lawyer, co-founder and CEO of the law firm ZAN PROTECT with offices in Almaty and Shymkent.`,
      'ab.p2': `My core specialization is litigation. I also practice digital law and corporate support, and I use OSINT — open-source intelligence — in my casework.`,
      'ab.p3': `I studied in Moscow: a bachelor's degree in criminal law and a master's degree in legal support of national security. I practice in Kazakhstan.`,
      'ab.p4': `I actively promote legal literacy: I speak at universities, to entrepreneurs and public officials, and create educational content.`,
      'ab.btn': `What I do`,
      'ab.phrole': `Lawyer · Litigation & digital law`,

      'sv.eyebrow': `Practice areas`,
      'sv.title': `How I<br><em>can help</em>`,
      'sv.ask': `Ask a question`,
      'sv.cta': `Discuss`,
      'sv.c1name': `Litigation`,
      'sv.c1body': `
          <p class="svc-desc">I represent clients in courts across Kazakhstan — from demand letter to judgment.</p>
          <ul class="svc-list">
            <li>Property disputes</li>
            <li>Recovery of debts and damages</li>
            <li>Corporate disputes</li>
            <li>Cross-border disputes involving foreign parties</li>
            <li>Disputes with state bodies under the Administrative Procedure Code</li>
          </ul>`,
      'sv.c2name': `Digital law`,
      'sv.c2body': `
          <ul class="svc-list">
            <li><b>Digital crimes:</b> legal assessment, filings, case support</li>
            <li><b>Digital assets:</b> cryptocurrency, P2P deals, disputes and fund recovery</li>
            <li><b>Personal data:</b> unlawful disclosure, business compliance</li>
            <li><b>Anti-fraud:</b> account and card freezes, lifting restrictions</li>
          </ul>`,
      'sv.c3name': `Corporate support`,
      'sv.c3body': `
          <p class="svc-desc">Contracts, pre-trial claims, changes to LLPs and sole proprietorships, support for IT companies, retainer services.</p>`,
      'sv.c4body': `
          <p class="svc-desc">Open-source intelligence. I use it in client casework. Lawful methods only.</p>
          <div class="svc-sub">For individuals</div>
          <ul class="svc-list">
            <li>Checking a person, seller or contractor before a deal</li>
            <li>Locating a debtor and their assets</li>
            <li>Gathering evidence for court</li>
          </ul>
          <div class="svc-sub">For business</div>
          <ul class="svc-list">
            <li>Vetting counterparties and partners before signing a contract</li>
            <li>Tracing a debtor's assets before enforcement</li>
            <li>Auditing the digital footprint of a company and its executives</li>
          </ul>`,

      'pr.eyebrow': `How I work`,
      'pr.title': `Work<br><em>process</em>`,
      'pr.s1t': `Review`,
      'pr.s1x': `You describe the situation and send the documents. I study everything available on the case.`,
      'pr.s2t': `Analysis`,
      'pr.s2x': `I check the facts, the evidence, the deadlines and the weak points of the position.`,
      'pr.s3t': `Qualification`,
      'pr.s3x': `I determine what it is from a legal standpoint and which rules apply.`,
      'pr.s4t': `Options`,
      'pr.s4x': `I explain the possible scenarios and the risks of each one.`,
      'pr.s5t': `Work`,
      'pr.s5x': `Only then do I take the case on.`,

      'why.eyebrow': `Why me`,
      'why.title': `What is<br><em>worth knowing</em>`,
      'why.i1t': `OSINT in casework`,
      'why.i1x': `I use open-source intelligence: I find information and turn it into evidence for court.`,
      'why.i2t': `Working across Kazakhstan`,
      'why.i2x': `Offices in Almaty and Shymkent. Court cases in other cities are handled remotely.`,
      'why.i3t': `The ZAN PROTECT team`,
      'why.i3x': `Lawyers for litigation, corporate and digital matters.`,
      'why.i4t': `Promoting legal literacy`,
      'why.i4x': `I speak at KazNU and Kunayev University and lecture for entrepreneurs and public officials.`,
      'why.i5t': `Confidentiality`,
      'why.i5x': `Everything stays private and confidential.`,

      'cta.eyebrow': `Get in touch`,
      'cta.title': `Discuss<br><em>your case</em>`,
      'cta.sub': `Message me on WhatsApp or Direct. Describe the situation and attach the documents.`,

      'ct.desc': `Lawyer. Litigation and digital law. Offices in Almaty and Shymkent, working remotely across Kazakhstan.`,
      'ct.colC': `Contacts`,
      'ct.colH': `Working hours`,
      'ct.cities': `Almaty & Shymkent · remote across Kazakhstan`,
      'ct.h1': `Mon–Fri: 9:00–19:00`,
      'ct.h2': `Sat: 10:00–15:00`,

      'ft.l1': `Kuralbek Shekherezada Zhan-Aidarkyzy. Lawyer. Litigation and digital law. Co-founder of ZAN PROTECT.`,
      'ft.l2': `© 2026 Kuralbek Shekherezada Zhan-Aidarkyzy. All rights reserved.`,
      'ft.privacy': `Privacy policy (KZ/RU)`,
      'ft.terms': `Terms of use (KZ/RU)`,
    },
  };

  // русский — из разметки
  const ru = {};
  document.querySelectorAll('[data-i]').forEach(el => {
    const k = el.dataset.i;
    if (!(k in ru)) ru[k] = el.innerHTML;
  });
  I18N.ru = ru;

  function apply(lang) {
    if (!I18N[lang]) lang = 'ru';
    const dict = I18N[lang];
    document.querySelectorAll('[data-i]').forEach(el => {
      const v = dict[el.dataset.i];
      if (v != null) el.innerHTML = v;
    });
    document.documentElement.lang = lang;
    document.title = META[lang].title;
    const meta = document.querySelector('meta[name="description"]');
    if (meta) meta.content = META[lang].desc;
    document.querySelectorAll('a[href*="wa.me"]').forEach(a => {
      a.href = 'https://wa.me/' + WA_PHONE + '?text=' + encodeURIComponent(WA_MSG[lang]);
    });
    document.querySelectorAll('.lang-switch button').forEach(b => {
      b.classList.toggle('on', b.dataset.lang === lang);
    });
    try { localStorage.setItem('lang', lang); } catch (e) {}
  }

  document.querySelectorAll('.lang-switch button').forEach(b => {
    b.addEventListener('click', () => apply(b.dataset.lang));
  });

  let saved = 'ru';
  try { saved = localStorage.getItem('lang') || 'ru'; } catch (e) {}
  apply(saved);
})();
