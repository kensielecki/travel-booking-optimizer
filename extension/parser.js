(function attachParser(root) {
  const KNOWN_PROGRAMS = [
    ["amex_mr", ["american express", "membership rewards", "amex"]],
    ["chase_ur", ["chase", "ultimate rewards"]],
    ["united", ["united", "mileageplus", "mileage plus"]],
    ["hilton", ["hilton", "honors"]],
    ["delta", ["delta", "skymiles", "sky miles"]],
    ["marriott", ["marriott", "bonvoy"]],
  ];

  const PROGRAM_NAMES = {
    amex_mr: "Amex Membership Rewards",
    chase_ur: "Chase Ultimate Rewards",
    united: "United MileagePlus",
    hilton: "Hilton Honors",
    delta: "Delta SkyMiles",
    marriott: "Marriott Bonvoy",
  };

  const KNOWN_MERCHANTS = [
    "Hilton",
    "United",
    "Delta",
    "Marriott",
    "Hyatt",
    "Air France",
    "British Airways",
    "Avianca",
  ];

  function normalizeSnapshot(snapshot, userId) {
    const program = detectProgram(snapshot);
    const balance = detectBalance(snapshot.text || "");
    const offers = detectOffers(snapshot.text || "", userId, program);
    const accounts = [];
    const warnings = [];

    if (program && balance !== null) {
      accounts.push({
        user_id: userId,
        program,
        display_name: displayNameForProgram(program),
        points_balance: balance,
      });
    }

    if (!program) {
      warnings.push("No supported loyalty program detected.");
    }

    if (program && balance === null) {
      warnings.push(`Detected ${displayNameForProgram(program)} but no balance.`);
    }

    if (program === "amex_mr" && offers.length === 0) {
      warnings.push("Detected Amex page but no offer-like rows.");
    }

    return {
      user_id: userId,
      source: "browser_extension",
      accounts,
      offers,
      metadata: {
        captured_at: snapshot.captured_at || new Date().toISOString(),
        page_title: snapshot.title || "",
        page_url_host: safeHost(snapshot.url || ""),
        detected_program: program,
        extraction_confidence: scoreConfidence(program, balance, offers),
        warnings,
      },
    };
  }

  function inspectPayloadSafety(payload) {
    const text = safetyTextForPayload(payload);
    const findings = [];
    const rules = [
      ["Possible long card/account number", /\b(?:\d[ -]*?){13,19}\b/],
      ["Possible SSN", /\b\d{3}-\d{2}-\d{4}\b/],
      ["Possible email address", /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i],
      ["Possible phone number", /\b(?:\+?1[ -.]?)?\(?\d{3}\)?[ -.]?\d{3}[ -.]?\d{4}\b/],
      ["Possible session or auth token", /\b(?:cookie|session|token|authorization|bearer|jwt)\b/i],
      ["Possible security code or 2FA text", /\b(?:2fa|two-factor|verification code|security code|one-time code|otp)\b/i],
      ["Possible street address", /\b\d{1,6}\s+[A-Za-z0-9.'-]+(?:\s+[A-Za-z0-9.'-]+){0,4}\s+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd)\b/i],
    ];

    for (const [label, pattern] of rules) {
      if (pattern.test(text)) {
        findings.push(label);
      }
    }

    return {
      ok: findings.length === 0,
      findings,
    };
  }

  function safetyTextForPayload(payload) {
    const accountText = (payload.accounts || [])
      .map((account) => [account.display_name, account.program, account.points_balance].join(" "))
      .join("\n");
    const offerText = (payload.offers || [])
      .map((offer) => [offer.merchant, offer.description, offer.value_usd, offer.min_spend_usd].join(" "))
      .join("\n");
    const metadataText = [
      payload.metadata?.page_title,
      payload.metadata?.page_url_host,
      ...(payload.metadata?.warnings || []),
    ].join("\n");
    return [accountText, offerText, metadataText].join("\n");
  }

  function detectProgram(snapshot) {
    const url = snapshot.url || "";
    const host = safeHost(url).toLowerCase();
    const title = (snapshot.title || "").toLowerCase();
    const hostAndTitle = `${host} ${title}`;
    const hostProgram = detectProgramFromText(hostAndTitle);

    if (hostProgram) {
      return hostProgram;
    }

    const haystack = `${url} ${title} ${snapshot.text || ""}`.toLowerCase();
    return detectProgramFromText(haystack);
  }

  function detectProgramFromText(haystack) {
    for (const [program, terms] of KNOWN_PROGRAMS) {
      if (terms.some((term) => haystack.includes(term))) {
        return program;
      }
    }
    return null;
  }

  function detectBalance(text) {
    const normalized = String(text).replace(/\u00a0/g, " ");
    const lineAwareBalance = detectAvailableBalanceByLine(normalized);
    if (lineAwareBalance !== null) {
      return lineAwareBalance;
    }

    const preferredPatterns = [
      /([\d,]{4,})[^\n]{0,36}(?:available\s+points|points\s+available)/i,
      /(?:available|available\s+points|points\s+available)[^\d\n]{0,48}([\d,]{4,})/i,
      /(?:current|total)[^\d]{0,24}(?:points|miles|balance)[^\d]{0,36}([\d,]{4,})/i,
    ];
    const patterns = [
      /(?:points|miles|balance|available|rewards)[^\d]{0,36}([\d,]{4,})/i,
      /([\d,]{4,})[^\n]{0,32}(?:points|miles|rewards)/i,
    ];

    for (const pattern of preferredPatterns) {
      const match = normalized.match(pattern);
      if (match) {
        return Number.parseInt(match[1].replaceAll(",", ""), 10);
      }
    }

    for (const pattern of patterns) {
      const match = normalized.match(pattern);
      if (match) {
        return Number.parseInt(match[1].replaceAll(",", ""), 10);
      }
    }
    return null;
  }

  function detectAvailableBalanceByLine(text) {
    const lines = String(text)
      .split(/\n+/)
      .map((line) => line.trim())
      .filter(Boolean);

    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index];
      if (!/(?:available|current|total).{0,16}(?:points|miles|balance)|(?:points|miles)\s+available/i.test(line)) {
        continue;
      }

      const sameLine = firstLargeNumber(line);
      if (sameLine !== null) {
        return sameLine;
      }

      const previousLine = lines[index - 1] || "";
      if (!/pending/i.test(previousLine)) {
        const previous = firstLargeNumber(previousLine);
        if (previous !== null) {
          return previous;
        }
      }

      const nextLine = lines[index + 1] || "";
      if (!/pending/i.test(nextLine)) {
        const next = firstLargeNumber(nextLine);
        if (next !== null) {
          return next;
        }
      }
    }

    return null;
  }

  function firstLargeNumber(text) {
    const match = String(text).match(/([\d,]{4,})/);
    return match ? Number.parseInt(match[1].replaceAll(",", ""), 10) : null;
  }

  function detectOffers(text, userId, program) {
    const offers = [];
    const lines = String(text)
      .split(/\n+/)
      .map((line) => line.trim())
      .filter(Boolean);

    for (const line of lines) {
      const value = detectOfferValue(line);
      if (value === null || !looksLikeOffer(line)) {
        continue;
      }

      offers.push({
        user_id: userId,
        program,
        merchant: detectMerchant(line),
        description: line.slice(0, 240),
        value_usd: value,
        min_spend_usd: detectMinimumSpend(line),
      });

      if (offers.length >= 5) {
        break;
      }
    }

    return offers;
  }

  function detectOfferValue(line) {
    const statementCredit = line.match(/(?:get|save|earn|receive)\s+\$([\d,]+(?:\.\d{2})?)/i);
    if (statementCredit) {
      return Number.parseFloat(statementCredit[1].replaceAll(",", ""));
    }

    const cashBack = line.match(/\$([\d,]+(?:\.\d{2})?)\s+(?:back|statement credit|cash back)/i);
    if (cashBack) {
      return Number.parseFloat(cashBack[1].replaceAll(",", ""));
    }

    return null;
  }

  function looksLikeOffer(line) {
    return /offer|cash back|statement credit|spend|save|get|receive|earn/i.test(line);
  }

  function detectMerchant(line) {
    const found = KNOWN_MERCHANTS.find((merchant) => line.toLowerCase().includes(merchant.toLowerCase()));
    return found || "Unknown merchant";
  }

  function detectMinimumSpend(line) {
    const match = line.match(/spend\s+\$([\d,]+(?:\.\d{2})?)/i);
    return match ? Number.parseFloat(match[1].replaceAll(",", "")) : 0;
  }

  function displayNameForProgram(program) {
    return PROGRAM_NAMES[program] || program;
  }

  function summarizePayload(payload) {
    const confidence = payload.metadata?.extraction_confidence;
    const suffix = typeof confidence === "number" ? `, ${Math.round(confidence * 100)}% confidence` : "";
    return `${payload.accounts.length} accounts, ${payload.offers.length} offers${suffix}`;
  }

  function scoreConfidence(program, balance, offers) {
    let score = 0;
    if (program) {
      score += 0.35;
    }
    if (balance !== null) {
      score += 0.4;
    }
    if (offers.length > 0) {
      score += 0.2;
    }
    if (offers.length > 1) {
      score += 0.05;
    }
    return Number(score.toFixed(2));
  }

  function safeHost(url) {
    try {
      return new URL(url).host;
    } catch {
      return "";
    }
  }

  root.LoyaltyParser = {
    detectBalance,
    detectAvailableBalanceByLine,
    detectMinimumSpend,
    detectOffers,
    detectProgram,
    detectProgramFromText,
    displayNameForProgram,
    normalizeSnapshot,
    scoreConfidence,
    inspectPayloadSafety,
    summarizePayload,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = root.LoyaltyParser;
  }
})(typeof globalThis !== "undefined" ? globalThis : window);
