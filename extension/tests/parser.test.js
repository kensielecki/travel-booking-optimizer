const assert = require("node:assert/strict");
const parser = require("../parser.js");

const USER_ID = "11111111-1111-4111-8111-111111111111";

function test(name, fn) {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`not ok - ${name}`);
    throw error;
  }
}

test("detects United program and mileage balance", () => {
  const snapshot = {
    url: "https://www.united.com/en/us/account",
    title: "United MileagePlus",
    text: "MileagePlus account\nAvailable miles 82,000\nPremier status progress",
  };

  const payload = parser.normalizeSnapshot(snapshot, USER_ID);

  assert.equal(payload.source, "browser_extension");
  assert.equal(payload.accounts.length, 1);
  assert.equal(payload.accounts[0].program, "united");
  assert.equal(payload.accounts[0].points_balance, 82000);
  assert.equal(payload.metadata.extraction_confidence, 0.75);
  assert.equal(payload.metadata.page_url_host, "www.united.com");
});

test("prioritizes United host over incidental Amex page text", () => {
  const snapshot = {
    url: "https://www.united.com/en/us/account",
    title: "Manage Your United MileagePlus Account | United Airlines",
    text: "MileagePlus available miles 20,826\nPay with American Express card ending somewhere else",
  };

  const payload = parser.normalizeSnapshot(snapshot, USER_ID);

  assert.equal(payload.accounts[0].program, "united");
  assert.equal(payload.metadata.detected_program, "united");
  assert.deepEqual(payload.metadata.warnings, []);
});

test("prefers available Chase points over pending points", () => {
  const snapshot = {
    url: "https://ultimaterewardspoints.chase.com/rewards-home",
    title: "Rewards Home - Ultimate Rewards - Chase",
    text: "Pending points 7,947\nAvailable points 24,318\nUse your Ultimate Rewards points",
  };

  const payload = parser.normalizeSnapshot(snapshot, USER_ID);

  assert.equal(payload.accounts[0].program, "chase_ur");
  assert.equal(payload.accounts[0].points_balance, 24318);
});

test("detects available Chase points in printed rewards page layout", () => {
  const snapshot = {
    url: "https://ultimaterewardspoints.chase.com/home",
    title: "Rewards Home - Ultimate Rewards - Chase",
    text: "Chase Sapphire Preferred\n24,224\nAvailable points\n7,947\nPending points\nYour earnings",
  };

  const payload = parser.normalizeSnapshot(snapshot, USER_ID);

  assert.equal(payload.accounts[0].program, "chase_ur");
  assert.equal(payload.accounts[0].points_balance, 24224);
});

test("detects Hilton Honors points with reversed wording", () => {
  const snapshot = {
    url: "https://www.hilton.com/en/hilton-honors/",
    title: "Hilton Honors",
    text: "180,000 Hilton Honors points available for your next stay",
  };

  const payload = parser.normalizeSnapshot(snapshot, USER_ID);

  assert.equal(payload.accounts[0].program, "hilton");
  assert.equal(payload.accounts[0].points_balance, 180000);
  assert.deepEqual(payload.metadata.warnings, []);
});

test("detects card offer value and minimum spend", () => {
  const offers = parser.detectOffers(
    "Amex Offers\nHilton: Spend $500 or more, get $100 back as a statement credit.\nUnited: Spend $300, receive $75 back.",
    USER_ID,
    "amex_mr",
  );

  assert.equal(offers.length, 2);
  assert.equal(offers[0].merchant, "Hilton");
  assert.equal(offers[0].value_usd, 100);
  assert.equal(offers[0].min_spend_usd, 500);
  assert.equal(offers[1].merchant, "United");
  assert.equal(offers[1].value_usd, 75);
  assert.equal(offers[1].min_spend_usd, 300);
});

test("returns empty account list when program or balance is missing", () => {
  const payload = parser.normalizeSnapshot(
    {
      url: "https://example.com",
      title: "Generic page",
      text: "No loyalty data here.",
    },
    USER_ID,
  );

  assert.deepEqual(payload.accounts, []);
  assert.equal(payload.metadata.extraction_confidence, 0);
  assert.deepEqual(payload.metadata.warnings, ["No supported loyalty program detected."]);
});

test("flags sensitive-looking payload content before send", () => {
  const finding = parser.inspectPayloadSafety({
    user_id: USER_ID,
    source: "browser_extension",
    accounts: [],
    offers: [
      {
        user_id: USER_ID,
        merchant: "Example",
        description: "Verification code 123456 for card 4111 1111 1111 1111",
        value_usd: 5,
        min_spend_usd: 0,
      },
    ],
  });

  assert.equal(finding.ok, false);
  assert.ok(finding.findings.includes("Possible long card/account number"));
  assert.ok(finding.findings.includes("Possible security code or 2FA text"));
});

test("passes normalized loyalty payload safety check", () => {
  const finding = parser.inspectPayloadSafety({
    user_id: USER_ID,
    source: "browser_extension",
    accounts: [
      {
        user_id: USER_ID,
        program: "amex_mr",
        display_name: "Amex Membership Rewards",
        points_balance: 110000,
      },
    ],
    offers: [
      {
        user_id: USER_ID,
        merchant: "Hilton",
        description: "Spend $500 or more, get $100 back.",
        value_usd: 100,
        min_spend_usd: 500,
      },
    ],
  });

  assert.equal(finding.ok, true);
});
