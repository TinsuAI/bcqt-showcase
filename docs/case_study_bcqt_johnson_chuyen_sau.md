# Case Study Chuyên Sâu: BCQT Johnson Health Tech 2025

Tài liệu này dùng để giúp partner hiểu sâu case BCQT đã làm cho Johnson: đã xử lý dữ liệu gì, kiểm soát thế nào, phát hiện gì ở Phase 3, điều tra thế nào ở Phase 4, lập mẫu ra sao ở Phase 5, và case này chứng minh năng lực gì khi trao đổi với cán bộ Hải quan.

## 1. Executive Summary

Johnson Health Tech Industry là doanh nghiệp chế xuất tại Bắc Ninh, sản xuất thiết bị thể thao/sức khỏe như máy chạy bộ, xe đạp tập, thiết bị gym. Công ty bắt đầu hoạt động từ tháng 6/2025, nên kỳ BCQT 2025 có đặc điểm quan trọng: tồn đầu kỳ bằng 0.

Team đã xây pipeline xử lý BCQT từ dữ liệu thật:

- SAP MB51: 243.421 dòng giao dịch kho.
- SAP MB5B: 20.064 mã vật tư sau làm sạch.
- Material Master: phân loại vật tư theo tài khoản kế toán, loại vật tư và hành vi thực tế.
- BCCT/VNACCS: 37.661 dòng tờ khai Hải quan.
- Output cuối: Mẫu 15, Mẫu 15a, Mẫu 16, working sheet theo mẫu đại lý, hồ sơ giải trình và các file audit.

Điểm quan trọng nhất: dự án không chỉ xuất biểu mẫu. Dự án xây được một hệ thống kiểm soát dòng vật tư từ nhập khẩu, kho, sản xuất, BOM, định mức đến báo cáo nộp Hải quan.

## 2. Bối Cảnh Nghiệp Vụ

Johnson là DNCX. Nguyên vật liệu nhập khẩu phục vụ sản xuất xuất khẩu được hưởng chính sách miễn thuế, nhưng doanh nghiệp phải chứng minh việc sử dụng nguyên liệu đó qua BCQT.

BCQT phải trả lời được các câu hỏi:

- Nguyên liệu nhập khẩu trong kỳ là những mã nào, số lượng bao nhiêu?
- Nguyên liệu đó đã xuất vào sản xuất bao nhiêu?
- Thành phẩm xuất khẩu là những mã nào, số lượng bao nhiêu?
- Một đơn vị thành phẩm xuất khẩu tiêu hao những nguyên liệu nào?
- Phần không đi vào xuất khẩu hiện nằm ở tồn NVL, tồn TP, tồn BTP, phế liệu, hao hụt hay trường hợp khác?
- Nếu Hải quan hỏi một mã cụ thể, có truy ngược được không?

Ba biểu mẫu chính:

- Mẫu 15: nhập-xuất-tồn nguyên liệu, vật tư.
- Mẫu 15a: nhập-xuất-tồn thành phẩm xuất khẩu.
- Mẫu 16: định mức thực tế NVL gốc cho từng thành phẩm xuất khẩu.

## 3. Dữ Liệu Đầu Vào

| Nguồn | Hệ thống | Nội dung | Quy mô |
|---|---|---|---:|
| MB51 | SAP | Giao dịch xuất/nhập kho T6-T12/2025 | 243.421 dòng |
| MB5B | SAP | Tồn kho, phát sinh nhập/xuất, Material Master | 20.064 mã sau clean |
| BCCT | VNACCS/Hải quan | Tờ khai nhập/xuất năm 2025 | 37.661 dòng |

Các khó khăn kỹ thuật/nghiệp vụ:

- SAP dùng giao diện tiếng Trung, cần chuẩn hóa tên cột.
- MB51 dùng Excel serial date, cần chuyển đúng ngày.
- MvT 101 có hai bản chất: nhập từ PO và nhập từ sản xuất.
- MB5B có nhiều sheet, có dữ liệu tồn kho và Material Master.
- BCCT là file `.xls` cũ, có dữ liệu tờ khai nhiều loại hình.
- Mã trên tờ khai có thể là mã SAP thật, mã mô tả nhóm, hoặc mã generic.
- Đơn vị tính giữa SAP và HQ có thể khác nhau.

## 4. Pipeline 6 Phase

| Phase | Mục tiêu | Output chính |
|---|---|---|
| Phase 1 | Chuẩn hóa và làm sạch dữ liệu thô | CLEAN_MB51, CLEAN_MB5B, CLEAN_BCCT |
| Phase 2 | Phân loại vật tư, enrich dữ liệu | CLEAN_MATERIAL_MASTER, ENRICHED_MB51, ENRICHED_MB5B |
| Phase 3 | Audit và kiểm tra chất lượng dữ liệu | AUDIT_PHASE3, CROSSCHECK_MB51_BAOCAO, CROSSCHECK_MB51_MB5B |
| Phase 4 | Điều tra bất thường và chốt rule xử lý | PHASE4_INVESTIGATION, MANUAL_REVIEW_SUMMARY, câu hỏi Johnson |
| Phase 5 | Lập Mẫu 15/15a/16 | SETTLEMENT_FORMS, WORKING_SHEET_BCQT, HO_SO_GIAI_TRINH |
| Phase 6 | Validation cuối kỳ | Validation sheet, so sánh phiên bản, test pass/fail |

## 5. Phase 1: Chuẩn Hóa Và Làm Sạch

Mục tiêu Phase 1 là đưa dữ liệu thô về dạng có thể xử lý bằng hệ thống.

Việc đã làm:

- Rename cột SAP tiếng Trung và BCCT tiếng Việt sang schema thống nhất.
- Chuyển ngày SAP từ Excel serial sang ngày thật.
- Dedup vật tư, group số liệu tồn kho theo mã.
- Loại dòng rác, dòng tổng, dòng không có ý nghĩa.
- Chuẩn hóa movement type và loại hình HQ.
- Loại 58.463 mã vật tư zero-activity không có GL, không có giao dịch, không nằm trong phạm vi quyết toán.

Kết quả:

- CLEAN_MB51_SAP: 243.421 dòng.
- CLEAN_MB5B_DETAIL: 20.064 mã.
- CLEAN_BCCT: 37.661 dòng.

Ý nghĩa khi nói với HQ/partner:

> Trước khi phân tích nghiệp vụ, team đã xử lý được bài toán data engineering: file lớn, định dạng khác nhau, schema không đồng nhất, dữ liệu có noise.

## 6. Phase 2: Phân Loại Vật Tư

Mục tiêu Phase 2 là xác định mỗi mã vật tư thuộc nhóm nào trong logic BCQT.

Phân loại ban đầu:

| Nhóm | Ý nghĩa | Số mã |
|---|---|---:|
| NVL | Nguyên vật liệu | 6.224 |
| BTP_NM | Bán thành phẩm ngoại mua | 8.509 |
| BTP_SX | Bán thành phẩm tự sản xuất | 2.437 |
| TP | Thành phẩm | 2.830 |
| CCDC | Công cụ dụng cụ | 64 |

Vấn đề phát hiện:

- 2.100 mã có mâu thuẫn phân loại giữa tài khoản kế toán và material type.
- 1.781 mã có material_type = HALB nhưng nằm trên TK 12150000, theo kế toán là NVL.
- 293 mã GL là BTP_NM nhưng material type là ROH.

Quyết định nghiệp vụ quan trọng:

- Ban đầu ưu tiên tài khoản kế toán để phân loại.
- Sau điều tra, có nhóm phải ưu tiên hành vi thực tế trên MB51.
- Phase 5 áp dụng nguyên tắc: hành vi thực tế > loại vật tư > tài khoản kế toán cho các case mâu thuẫn.

Ý nghĩa:

> Phân loại vật tư không thể chỉ nhìn một cột master data. Phải đối chiếu kế toán, material type, tờ khai HQ và hành vi sản xuất thực tế.

## 7. Phase 3: Audit Và Kiểm Tra Chất Lượng Dữ Liệu

Phase 3 là phần rất quan trọng để chứng minh năng lực kiểm soát. Trước khi lập Mẫu 15/15a/16, team chạy hệ thống kiểm tra chéo và audit chất lượng dữ liệu.

Dữ liệu đầu vào Phase 3:

- ENRICHED_MB51: 243.421 dòng.
- ENRICHED_MB5B: 20.064 mã.
- CLEAN_BCCT: 37.661 dòng.

Kết quả tổng:

| Nhóm | Nội dung | Số test | Findings |
|---|---|---:|---:|
| XC | Đối chiếu chéo SAP-HQ và SAP-SAP | 5 | 3.761 |
| A | Pattern SAP-HQ | 5 | 11.095 |
| B | Kiểm tra nội bộ dữ liệu HQ | 5 | 1.186 |
| C | Kiểm tra nội bộ SAP | 1 | 236 |
| D | Kiểm tra sản xuất | 1 | 2.522 |
| Tổng | | 17 test | 18.800 |

File kết quả chính: `AUDIT_PHASE3.xlsx`, gồm Summary, 13 sheet test và 5 sheet crosscheck.

### 7.1 Crosscheck XC1: SAP vs HQ Nhập Khẩu

Logic:

- SAP side: MB51 MvT 101/102 có PO.
- HQ side: tờ khai E11, E13, E15, G12, G13.
- Group theo mã vật tư, so tổng số lượng và trị giá.

Kết quả:

| Trạng thái | Số mã | Ý nghĩa |
|---|---:|---|
| EXACT_MATCH | 3.805 | Khớp hoàn toàn |
| CLOSE_MATCH | 194 | Chênh dưới 5% |
| DISCREPANCY | 488 | Chênh từ 5% trở lên |
| SAP_ONLY | 84 | SAP có nhập, HQ không có |
| CUSTOMS_ONLY | 1.037 | HQ có, SAP không có |

Ghi chú quan trọng:

- Trong 1.037 CUSTOMS_ONLY, có 1.002 mã là E13 generic như MC, OTHERS, DC-SON, không phải mã vật tư SAP thật.
- Top chênh lệch nổi bật: K60000900, SAP 60.000 vs HQ 60, sai đơn vị ×1.000.

Ý nghĩa:

> Đây là bài kiểm giúp phát hiện ngay các mã nhập khẩu không khớp giữa sổ kho doanh nghiệp và tờ khai Hải quan.

### 7.2 Crosscheck XC2: SAP vs HQ Xuất Khẩu E42

Logic:

- SAP side: MvT 901/902.
- HQ side: E42.
- Group theo mã thành phẩm.

Kết quả:

| Trạng thái | Số mã |
|---|---:|
| EXACT_MATCH | 487 |
| DISCREPANCY | 30 |
| CUSTOMS_ONLY | 7 |

Nhận định:

- Xuất khẩu khớp tốt: 487/524 mã, khoảng 93%.
- 30 mã chênh lệch nhỏ, tổng chênh 6 đơn vị.

### 7.3 Crosscheck XC4: MB51 vs MB5B Biến Động Ròng

Logic:

- Johnson mới hoạt động, tồn đầu kỳ bằng 0.
- Net movement theo MB51 phải khớp biến động tồn kho theo MB5B.

Kết quả:

- 20.063/20.064 mã khớp gần hoàn hảo.
- Duy nhất 1 mã lệch: K40000011, chênh -972,3 đơn vị.
- MB51-only net zero đều là chuyển kho nội bộ, không phải lỗi.

Ý nghĩa:

> Dữ liệu SAP nội bộ có tính nhất quán rất cao ở biến động ròng. Điều này cho phép dùng SAP làm nguồn cho xuất sản xuất và định mức, nhưng vẫn phải đối chiếu với HQ cho nhập/xuất qua biên giới.

### 7.4 T01: Phân Loại Mâu Thuẫn Giữa Tờ Khai Và Hành Vi SAP

T01 phát hiện khi cách khai trên HQ mâu thuẫn với hành vi sử dụng trong SAP.

Kết quả chính:

- 303 mã khai E13 nhưng SAP có MvT 261 xuất cho sản xuất.
- 583 mã khai E11 nhưng SAP không có tiêu hao sản xuất.
- Trong nhóm E11, có 289 mã E11_NO_SAP_RECEIPT: khai nhập HQ nhưng SAP không có nhập kho PO.

Ý nghĩa nghiệp vụ:

- E13 thường là máy móc/thiết bị.
- Nếu một mã khai E13 nhưng lại bị xuất cho sản xuất như NVL, cần hỏi: đây là máy móc, CCDC, hay vật tư tiêu hao bị khai sai loại hình?

### 7.5 T02: Chênh Lệch Số Lượng SAP vs HQ

T02 so SAP MvT 101/102 có PO với HQ E11/E15, theo từng mã.

Kết quả:

| Nhóm | Số mã | Mức độ |
|---|---:|---|
| MINOR_DIFF dưới 5% | 229 | Info |
| MODERATE_DIFF 5-20% | 196 | Warning |
| MAJOR_DIFF trên 20% | 241 | Critical |
| UOM_MISMATCH ×1.000 | 3 | Critical |
| MISSING_SAP | 298 | Critical |
| MISSING_HQ | 83 | Critical |

Ba mã sai đơn vị:

| Mã | SAP | HQ | Tỷ lệ |
|---|---:|---:|---:|
| K60000201 | 6.000 | 6 | ×1.000 |
| K60000900 | 60.000 | 60 | ×1.000 |
| 1000459277 | 20 | 20.000 | ×0,001 |

Ý nghĩa:

> Nếu không phát hiện sai đơn vị trước khi lập Mẫu 15, báo cáo sẽ sai lớn. Đây là ví dụ cụ thể cho thấy audit dữ liệu trước khi lập mẫu là bắt buộc.

### 7.6 T03: Trả NCC Thiếu Tờ Khai B13

Kết quả:

- 268 mã có MvT 122 trong SAP.
- Tổng 88.527 đơn vị, 922 dòng.
- Không có tờ khai B13 trong dữ liệu HQ.

Ban đầu cần hỏi Johnson:

- Có dùng B13 cho trả hàng nhà cung cấp không?
- Nếu không, dùng loại hình nào?
- Có tờ khai trả hàng ngoài phạm vi dữ liệu không?

Kết quả sau điều tra:

- Johnson xác nhận/logic dữ liệu cho thấy MvT 122/123 trong case này là bút toán điều chỉnh nhập kho, không phải trả hàng NCC.
- 256/268 mã có tổng 101+102+122+123 khớp HQ, xác nhận bản chất điều chỉnh.

Ý nghĩa:

> Một movement type không thể hiểu máy móc theo tài liệu SAP chung. Phải kiểm lại bằng dữ liệu thực tế và xác nhận nghiệp vụ doanh nghiệp.

### 7.7 T04: So Sánh Nhập Theo Tháng

T04 so nhập kho SAP với HQ theo từng tháng và từng mã.

Kết quả theo material-month:

| Flag | Số dòng | Ý nghĩa |
|---|---:|---|
| MATCH | 5.662 | Cùng tháng, cùng số lượng |
| MISMATCH | 3.391 | Cùng tháng nhưng số lượng khác |
| SAP_ONLY | 2.243 | SAP có, HQ không có trong tháng |
| HQ_ONLY | 3.098 | HQ có, SAP không có trong tháng |
| HQ_ONLY_PRE_T6 | 2 | HQ trước T6, MB51 chưa có data |

Ý nghĩa:

> T04 không chỉ tìm tổng lệch, mà chỉ ra lệch theo timing. Điều này giúp phân biệt sai thật với lệch kỳ ghi nhận.

### 7.8 T05: Cùng Mã Nhiều Loại Hình HQ

Kết quả:

- 962 mã xuất hiện trên từ 2 loại hình HQ trở lên.
- 562 mã là conflict, ví dụ cùng mã vừa E11 vừa E13.

Ý nghĩa:

> Cùng một mã nếu vừa khai là NVL vừa khai là máy móc thì rủi ro phân loại rất rõ. Đây là nhóm câu hỏi quan trọng khi làm việc với doanh nghiệp.

### 7.9 T09: Mã HS Không Nhất Quán

Kết quả:

| Mức độ | Số mã | Ý nghĩa |
|---|---:|---|
| Critical | 25 | Khác chapter, tức khác 2 số đầu HS |
| Warning | 6 | Khác heading |
| Info | 11 | Khác subheading |

Ý nghĩa:

> HS khác chapter là rủi ro pháp lý lớn, vì bản chất phân loại hàng hóa khác nhau hoàn toàn.

### 7.10 T11: Tồn Kho Âm

Kết quả:

- 236 mã có tồn kho âm tại ít nhất một thời điểm khi tính cộng dồn theo ngày.

Ý nghĩa:

> Với tồn đầu kỳ bằng 0, tồn âm nghĩa là có xuất trước nhập hoặc thiếu nguồn nhập trong dữ liệu. Đây là nhóm cần giải trình khi HQ kiểm tra.

### 7.11 T12: Định Mức Bất Thường Giữa Lệnh SX

T12 kiểm tra độ ổn định định mức thực tế giữa các lệnh sản xuất.

Kết quả:

- 1.779 thành phẩm có từ 2 lệnh sản xuất trở lên.
- 17.483 cặp thành phẩm-NVL được kiểm tra.
- 2.522 cặp có định mức dao động lớn.

Ý nghĩa:

> T12 giúp phát hiện sản xuất bất thường, thay đổi thiết kế, hao hụt không đều hoặc ghi nhận sai lệnh. Sau đó team quyết định không xử lý T12 ở Phase 4 nữa mà kiểm trực tiếp khi xây Mẫu 16 ở Phase 5.

### 7.12 T13: NVL Tiêu Hao Không Có Nhập

Kết quả:

- 157 mã NVL/BTP_NM có tiêu hao sản xuất nhưng không có tờ khai nhập E11/E15 tương ứng.

Câu hỏi:

- Đây là NVL nội địa?
- Hay thiếu tờ khai?
- Hay phân loại vật tư sai?

## 8. Phase 4: Điều Tra Bất Thường

Phase 4 không chỉ liệt kê findings. Phase 4 gom findings theo mã vật tư, nhận diện pattern, phân loại mức độ ảnh hưởng và chuẩn bị câu hỏi.

Kết quả Run 2:

| Nhóm | Số mã | Ý nghĩa |
|---|---:|---|
| Không có finding | 15.618 | Dữ liệu sạch |
| AUTO_OK | 2.591 | Có finding nhưng không ảnh hưởng |
| AUTO_EXCLUDE | 748 | Ngoài phạm vi hoặc không đối chiếu được |
| REVIEW | 1.428 | Pattern đã nhận diện, cần review/hỏi |
| MANUAL_REVIEW | 424 | Phức tạp, cần xem tay |

Ưu tiên xử lý:

| Nhóm | Số mã | Deadline |
|---|---:|---|
| BLOCKING_P5 | 976 | Phải giải quyết trước khi lập mẫu |
| BLOCKING_SUBMISSION | 629 | Phải giải quyết trước khi nộp |
| NON_BLOCKING | 3.586 | Ghi nhận |

Các vấn đề BLOCKING_P5:

- 480 mã NVL khai cả E11/E13 hoặc E13 nhưng có tiêu hao sản xuất.
- 268 mã MvT 122/123 cần xác định bản chất.
- 157 mã NVL tiêu hao không có nhập E11/E15.
- 1.781 mã HALB trên TK 12150000 cần xác nhận phân loại.

Các vấn đề BLOCKING_SUBMISSION:

- 424 mã manual review.
- 205 mã tồn kho âm.
- 42 mã HS không nhất quán.

Ý nghĩa:

> Phase 4 là bước biến 18.800 findings thành danh sách vấn đề có thứ tự ưu tiên. Đây là chỗ thể hiện năng lực phân tích dữ liệu và nghiệp vụ, không chỉ chạy script.

## 9. Các Câu Hỏi Gửi Johnson

Từ Phase 3-4, team gom thành nhóm câu hỏi nghiệp vụ:

BLOCKING_P5:

1. Ba mã sai đơn vị tính ×1.000: K60000201, K60000900, 1000459277.
2. 300 mã NVL khai cả E11 và E13.
3. 268 mã có MvT 122 nhưng không có B13.
4. 157 mã NVL tiêu hao nhưng không có tờ khai nhập E11/E15.
5. 1.781 mã HALB trên TK 12150000, xác nhận phân loại là NVL hay BTP.

BLOCKING_SUBMISSION:

6. 962 mã xuất hiện trên nhiều loại hình HQ.
7. 42 mã HS không nhất quán, trong đó 25 mã khác chapter.
8. 236 mã tồn kho âm.

NON_BLOCKING:

9. MvT 903 có liên quan BCQT không.

Ý nghĩa:

> Team không tự kết luận khi dữ liệu chưa đủ. Các điểm chưa chắc được chuyển thành câu hỏi xác nhận, có số mã, tác động và deadline rõ.

## 10. Phase 5: Lập Mẫu 15/15a/16

Phase 5 là giai đoạn lập biểu mẫu quyết toán.

Kết quả chính:

| Mẫu | Nội dung | Số dòng |
|---|---|---:|
| Mẫu 15 | Nhập-xuất-tồn NVL | 4.773 |
| Mẫu 15a | Nhập-xuất-tồn TP xuất khẩu | 517 |
| Mẫu 16 | Định mức thực tế | 42.678 |

Kiểm tra tự động: 9/9 PASS.

### 10.1 Nguyên Tắc Xử Lý Mẫu 15

Cấu trúc nguồn số liệu:

| Cột | Nội dung | Nguồn |
|---|---|---|
| Tồn đầu kỳ | Tồn đầu | 0, vì Johnson mới hoạt động T6/2025 |
| Nhập trong kỳ | Nhập NVL | Số Hải quan E11/E15/E13 trong scope |
| Tái xuất | B13 | 0, không có B13 |
| Xuất sản xuất | Tiêu hao sản xuất | SAP MvT 261/262 |
| Xuất khác | Phế liệu | SAP MvT 201/202 |
| Tồn cuối | Balance equation | Nhập - xuất = tồn |

Kết quả đối chiếu:

- Tổng nhập Mẫu 15: 8.784.519.
- Tổng nhập Hải quan cùng scope: 8.784.519.
- Chênh lệch: 0.
- Khớp per-material: 4.773/4.773, tức 100%.

Điểm quan trọng:

> Mẫu 15 nhập khớp HQ 100%, nhưng không giấu chênh lệch với SAP. Những chênh lệch được chuyển vào tồn cuối/ghi chú theo rule rõ.

### 10.2 Tồn Cuối Mẫu 15

Nhóm tồn cuối:

| Nhóm | Số mã | Giải thích |
|---|---:|---|
| Khớp MB5B | 3.633 | Nhập HQ = SAP |
| Thử khuôn | 553 | HQ có nhập, SAP chưa nhập kho, tồn = nhập |
| T02 điều chỉnh | 656 | Nhập HQ khác SAP, tồn = MB5B + delta |
| FIFO nguồn kép bị giới hạn | 207 | Mẫu 15 chỉ theo dõi phần nhập khẩu |
| Nguồn kép không bị giới hạn | 379 | Source tracking, nhập khẩu đủ cung |

Tổng có chênh lệch: 1.140 mã, tất cả có nguyên nhân và ghi chú.

### 10.3 Mẫu 15a

Phạm vi:

- 2.747 thành phẩm trong master.
- 517 mã có tờ khai E42 xuất khẩu.
- Mẫu 15a cuối cùng: 517 mã.

Nguồn số liệu:

- Nhập kho TP: SAP MvT 101/102 production receipt.
- Xuất khẩu: số Hải quan E42.
- Xuất khác: TP vai trò kép MvT 261/262, 112 mã, 1.059 đơn vị.
- Tồn cuối: MB5B.

Kết quả:

- 493/517 mã cân bằng.
- 24 mã chênh lệch, tổng 153 đơn vị, do E42 khác SAP MvT 901/902.

### 10.4 Mẫu 16: Định Mức Thực Tế

Mẫu 16 là phần khó nhất.

Kết quả:

| Chỉ số | Giá trị |
|---|---:|
| Lệnh sản xuất phân tích | 23.227 |
| Thành phẩm xuất khẩu có định mức | 517 |
| NVL đầu vào cấp 1 | 4.096 |
| Tổng dòng Mẫu 16 | 42.678 |

Nguyên tắc:

- Định mức = tổng tiêu hao thực tế / tổng sản lượng thực tế.
- BTP tự sản xuất không phải là NVL gốc để trình bày cuối cùng.
- BOM nhiều cấp phải flatten về NVL gốc.
- Nếu mã có tờ khai HQ thì giữ ở cấp 1 vì HQ theo dõi mã đó qua biên giới.

Phân cấp:

| Cấp | Định nghĩa | Số mã | Xử lý |
|---|---|---:|---|
| Cấp 1 | Chỉ là input hoặc có tờ khai HQ | 17.013 | Giữ trên Mẫu 16 |
| Cấp 2+ | Vừa input vừa output, không có HQ | 2.534 | Quy đổi về NVL gốc |
| TP | Có MvT 901/902 xuất khẩu | 517 | Cột thành phẩm |

## 11. Các Bài Toán Khó Ở Phase 5

### 11.1 T02: Lấy SAP Hay HQ?

Vấn đề:

- 1.050 mã có chênh lệch số lượng nhập giữa SAP và HQ.

Quyết định cuối:

- Theo phản hồi Johnson, tất cả lấy số Hải quan cho nhập trong kỳ.
- Tiêu hao sản xuất giữ nguyên theo SAP.
- Tồn cuối điều chỉnh theo delta giữa HQ và SAP.

Công thức:

```text
Tồn cuối = MB5B + (Nhập HQ - Nhập SAP)
```

Ý nghĩa:

> Vì BCQT nộp cho HQ, phần nhập phải khớp dữ liệu tờ khai. Nhưng hệ thống không bẻ tiêu hao để làm đẹp số liệu; chênh lệch đi vào tồn và ghi chú.

### 11.2 MvT 122/123: Trả Hàng Hay Điều Chỉnh?

Ban đầu Phase 3 coi MvT 122 là trả hàng NCC, dẫn tới 268 findings thiếu B13.

Sau điều tra:

- Johnson dùng 122/123 như bút toán điều chỉnh nhập kho.
- 243/268 hoặc 256/268 mã tùy ngưỡng kiểm có net SAP khớp HQ khi tính 101+102+122+123.

Quyết định:

- Không xử lý như trả hàng NCC trong BCQT.
- Khi nhập lấy số HQ, 122/123 không cộng riêng vào nhập để tránh double count.

Ý nghĩa:

> Một mã MvT phải được hiểu theo thực tế vận hành doanh nghiệp, không chỉ theo định nghĩa sách vở.

### 11.3 Vật Tư Nguồn Kép

Vấn đề:

- 556 mã vừa nhập khẩu vừa tự sản xuất nội bộ.
- Mẫu 15 chỉ theo dõi phần nhập khẩu.
- Phần tự sản xuất là BTP nội bộ, không nên làm sai scope Mẫu 15.

Quyết định:

- Theo dõi source bằng FIFO.
- Ưu tiên dùng phần nhập khẩu trước.
- Xuất sản xuất trên Mẫu 15 giới hạn ở mức nguồn nhập khẩu.
- Phần tiêu thụ vượt nhập khẩu được xem là nguồn tự sản xuất, giải trình qua NVL gốc.

Kết quả:

| Chỉ số | Giá trị |
|---|---:|
| Mã nguồn kép | 556 |
| Bị giới hạn xuất SX | 207 |
| Nhập khẩu còn tồn | 379 |

Ý nghĩa:

> Đây là bài toán BCQT khó vì cùng một mã vật tư có hai nguồn. Nếu không tách nguồn, Mẫu 15 và Mẫu 16 sẽ dễ mâu thuẫn.

### 11.4 CCDC Và E13

Vấn đề:

- 64 mã trên tài khoản CCDC.
- Có mã CCDC là vật tư tiêu hao, có mã là máy móc/thiết bị thật.

Rule:

- Nếu nhập E11/E15 và có hành vi tiêu hao → vào Mẫu 15.
- Nếu E13 máy móc/thiết bị và không tiêu hao → loại khỏi Mẫu 15.

Kết quả:

- 25 mã CCDC có tờ khai nhập khẩu vào Mẫu 15.
- 1.010 mã E13 không có tiêu hao được loại khỏi Mẫu 15.

### 11.5 BOM Nhiều Cấp Và Vòng Lặp Sản Xuất

Vấn đề:

- BOM không chỉ một cấp.
- Có TP dùng BTP, BTP lại dùng NVL.
- Có vòng lặp chuyển đổi phiên bản: A dùng B, B dùng A.
- Có self-loop/rework.

Cách xử lý:

- Dùng topological sort để flatten BOM không có cycle.
- Dùng Tarjan SCC để phát hiện vòng lặp.
- Dùng hệ phương trình tuyến tính để giải cycle:

```text
X = K + C × X
(I - C) × X = K
```

Quy mô:

- 20 nhóm vòng lặp.
- 44 mã trong các vòng lặp.
- 150 lệnh chuyển đổi phiên bản, khoảng 0,6% tổng lệnh sản xuất.
- Tất cả 517 TP xuất khẩu vẫn có định mức.

Ý nghĩa:

> Đây là phần chứng minh năng lực thuật toán và hiểu sản xuất. Nếu xử lý thủ công hoặc bỏ qua cycle, Mẫu 16 có thể thiếu hoặc tính trùng định mức.

## 12. Phase 6: Validation Cuối Kỳ

Validation cuối kiểm tra các bất biến trước khi chốt.

Các test tiêu biểu:

| # | Kiểm tra | Kết quả |
|---|---|---|
| 1 | NVL Mẫu 16 nằm trong Mẫu 15 | PASS |
| 2 | TP Mẫu 16 nằm trong Mẫu 15a | PASS |
| 3 | Không có BTP cấp 2+ trên Mẫu 16 | PASS |
| 4 | Tổng nhập Mẫu 15 khớp HQ | PASS, chênh 0,0% |
| 5 | Tổng xuất Mẫu 15a khớp E42 | PASS, chênh 0,1% |
| 6 | Tồn cuối vs MB5B có giải trình | PASS |
| 7 | Đối chiếu M15-M16 | PASS |
| 8 | TP Mẫu 15a có Mẫu 16 | PASS |
| 9 | CCDC scope | PASS |

Kết quả showcase v12.0:

- Mẫu 15: 4.773 dòng.
- Mẫu 15a: 517 dòng.
- Mẫu 16: 42.676/42.678 dòng tùy version báo cáo.
- Traceability đạt khoảng 99,9%.
- Residual NVL chưa truy được: 6.619 đơn vị, khoảng 0,14% tổng xuất sản xuất, có hướng giải trình hao hụt/cắt dập.

## 13. Hồ Sơ Đầu Ra

Các artifact chính:

| File | Nội dung |
|---|---|
| `AUDIT_PHASE3.xlsx` | 13 test + 5 crosscheck, 19 sheets |
| `CROSSCHECK_MB51_BAOCAO.xlsx` | Đối chiếu SAP-HQ nhập, xuất E42, E13 |
| `CROSSCHECK_MB51_MB5B.xlsx` | Đối chiếu MB51-MB5B |
| `PHASE4_INVESTIGATION.xlsx` | Điều tra bất thường, pattern, câu hỏi |
| `MANUAL_REVIEW_SUMMARY.xlsx` | Tổng hợp review thủ công |
| `SETTLEMENT_FORMS_v12.0.xlsx` | 14 sheets: Mẫu 15, 15a, 16, validation, traceability |
| `WORKING_SHEET_BCQT_v12.0.xlsx` | Working sheet theo mẫu đại lý |
| `HO_SO_GIAI_TRINH_v12.0.xlsx` | Hồ sơ giải trình nội bộ, BOM, traceability, validation |
| `AUDIT_Q1.xlsx` | Audit định kỳ Q1/2026 |

## 14. Q1/2026: Mở Rộng Từ BCQT Sang Kiểm Soát Định Kỳ

Sau BCQT 2025, team mở rộng sang audit Q1/2026.

Kết quả Q1:

- 3 source files cleaned: MB51 128K dòng, MB5B 7,3K mã active, BCCT 14,6K dòng, 778 tờ khai.
- Khung kiểm soát 4 tầng, 6 bài test.
- 1.415 phát hiện, 701 mức nghiêm trọng.
- 11 câu hỏi gửi Johnson.

Một số phát hiện Q1:

- Xuất khẩu SAP thấp hơn HQ khoảng 19%, cần xác định timing hay giá.
- 28 mã mới Q1 cần xác nhận phân loại.
- MvT 543 project stock cần xác nhận scope BCQT.
- MvT 311/411 tăng mạnh, cần hỏi có thay đổi quy trình kho không.
- E13 tăng 118%, cần xác định mục đích nhập.
- 170 mã có SAP nhưng không có HQ, 26 mã có HQ nhưng không có SAP.

Ý nghĩa:

> Sau khi làm BCQT năm, cùng framework có thể dùng để kiểm soát định kỳ theo quý, phát hiện vấn đề sớm trước kỳ quyết toán tiếp theo.

## 15. Case Johnson Chứng Minh Năng Lực Gì

### 15.1 Năng lực hệ thống

- Xử lý dữ liệu lớn nhiều nguồn.
- Chuẩn hóa file Excel phức tạp.
- Xây pipeline có version, artifact, validation.
- Tạo web showcase để trình bày quy trình và truy vết.
- Có thể chuyển logic nghiệp vụ thành rule có thể chạy lại.

### 15.2 Năng lực phân tích dữ liệu

- Đối chiếu chéo SAP-HQ, SAP-SAP.
- Tách false positive khỏi rủi ro thật.
- Gom 18.800 findings thành nhóm ưu tiên.
- Nhận diện pattern như sai UOM ×1.000, E13 tiêu hao như NVL, thiếu B13, tồn âm, HS khác chapter.
- Theo dõi issue sang kỳ Q1/2026.

### 15.3 Năng lực nghiệp vụ BCQT

- Hiểu Mẫu 15, 15a, 16.
- Hiểu DNCX, E11/E15/E42/E13/B13/G22.
- Hiểu nguyên tắc nhập khớp HQ, xuất sản xuất theo dữ liệu kho, tồn cuối phải có giải trình.
- Hiểu BTP tự sản xuất phải flatten về NVL gốc.
- Hiểu CCDC/vật tư tiêu hao/máy móc phải tách scope.
- Hiểu cách đặt câu hỏi cho doanh nghiệp khi chưa đủ căn cứ.

### 15.4 Năng lực thuật toán

- Weighted average norm.
- BOM flatten nhiều cấp.
- Tarjan SCC để phát hiện cycle.
- Linear solver cho vòng lặp sản xuất.
- FIFO/source tracking cho dual-source.
- Validation bất biến cuối kỳ.

## 16. Cách Kể Case Johnson Với Cán Bộ HQ

Không nên kể Johnson như “chúng tôi có SAP nên kiểm được”. Nên kể:

> Case Johnson là bằng chứng team đã xử lý được một hồ sơ BCQT phức tạp từ dữ liệu doanh nghiệp và tờ khai. Qua đó team hiểu các điểm rủi ro mà HQ thường phải kiểm: nhập lệch tờ khai, xuất lệch E42, định mức bất thường, loại hình E13/E11 lẫn nhau, HS không nhất quán, tồn âm, vật tư nguồn kép, BTP tự sản xuất. Nếu áp dụng cho phía HQ, lớp đầu tiên không cần SAP; chỉ cần tờ khai và bộ BCQT doanh nghiệp nộp là có thể chạy risk screening. Khi kiểm tra sâu và doanh nghiệp cung cấp dữ liệu nội bộ, những kỹ thuật từ Johnson có thể dùng để audit sâu hơn.

## 17. Script 3 Phút Về Case Johnson

> Với Johnson, team em xử lý một bộ dữ liệu BCQT thật của doanh nghiệp chế xuất sản xuất thiết bị thể thao. Dữ liệu gồm 243 nghìn dòng biến động kho SAP, 20 nghìn mã vật tư, và hơn 37 nghìn dòng tờ khai Hải quan.
>
> Team không đi thẳng vào lập Mẫu 15, 15a, 16. Trước tiên hệ thống chuẩn hóa dữ liệu, phân loại vật tư, rồi chạy Phase 3 audit gồm 17 bài kiểm và 5 nhóm đối chiếu. Phase 3 phát hiện 18.800 findings, trong đó có các vấn đề rất thực tế như 3 mã sai đơn vị tính ×1.000, hơn 300 mã khai E13 nhưng lại tiêu hao như nguyên liệu, 268 mã có MvT 122 nhưng không có B13, 236 mã tồn âm, và 25 mã HS khác chapter.
>
> Sau đó Phase 4 gom findings thành nhóm ưu tiên: cái nào blocking trước khi lập mẫu, cái nào blocking trước khi nộp, cái nào chỉ ghi nhận. Những điểm chưa chắc được chuyển thành câu hỏi gửi Johnson, không tự kết luận.
>
> Phase 5 mới lập mẫu: Mẫu 15 có 4.773 dòng, Mẫu 15a có 517 thành phẩm xuất khẩu, Mẫu 16 có khoảng 42,6 nghìn dòng định mức. Phần khó nhất là xử lý BOM nhiều cấp, vật tư nguồn kép, CCDC/E13, và vòng lặp sản xuất. Hệ thống flatten BTP tự sản xuất về NVL gốc, xử lý cycle bằng thuật toán, và chạy validation cuối kỳ 9/9 pass.
>
> Case này cho thấy team không chỉ làm Excel, mà hiểu cách kiểm soát dòng vật tư và xây được hệ thống truy vết, audit, giải trình. Khi nói với HQ, mình không nói HQ có SAP; mình nói từ kinh nghiệm Johnson, team có thể xây lớp risk screening trên dữ liệu tờ khai và bộ BCQT đã nộp, sau đó audit sâu hơn khi doanh nghiệp cung cấp dữ liệu nội bộ.

## 18. Những Số Liệu Nên Nhớ

- 243.421 dòng MB51.
- 20.064 mã vật tư sau làm sạch.
- 37.661 dòng BCCT.
- 2.100 mã mâu thuẫn phân loại master data.
- 18.800 findings Phase 3.
- 17 bài kiểm Phase 3, gồm 13 test và 5 crosscheck.
- 3 mã sai đơn vị ×1.000.
- 303 mã E13 nhưng có tiêu hao sản xuất.
- 268 mã MvT 122 không có B13, sau xác minh là điều chỉnh nhập kho.
- 236 mã tồn kho âm.
- 42 mã HS không nhất quán, 25 mã khác chapter.
- 976 mã BLOCKING_P5 ở Phase 4.
- 4.773 dòng Mẫu 15.
- 517 mã Mẫu 15a.
- Khoảng 42.676-42.678 dòng Mẫu 16.
- 556 mã vật tư nguồn kép.
- 20 nhóm vòng lặp sản xuất, 44 mã.
- 9/9 validation pass.
- Traceability khoảng 99,9%.

## 19. Điểm Cần Cẩn Trọng Khi Kể

- Không nói Johnson là mô hình dữ liệu của HQ. Johnson là case doanh nghiệp.
- Không nói HQ có SAP. HQ có tờ khai và báo cáo doanh nghiệp nộp.
- Không khẳng định mọi chênh lệch là sai. Chênh lệch là dấu hiệu cần phân loại và hỏi.
- Không nói tool thay cán bộ kết luận. Tool giúp phát hiện, ưu tiên, truy vết và chuẩn bị câu hỏi.
- Không đi quá sâu thuật toán nếu người nghe chưa hỏi. Chỉ nói: có BOM nhiều cấp và vòng lặp, team đã xử lý được bằng thuật toán có validation.

## 20. Kết Luận

Case Johnson là bằng chứng mạnh nhất hiện tại cho ba năng lực:

1. Xây hệ thống xử lý dữ liệu BCQT thực tế, không chỉ làm file Excel.
2. Phân tích và kiểm soát rủi ro bằng dữ liệu, đặc biệt ở Phase 3-4.
3. Hiểu sâu nghiệp vụ BCQT đủ để xử lý các tình huống khó như nguồn kép, E13/CCDC, MvT 122, sai UOM, BOM nhiều cấp và vòng lặp sản xuất.

Thông điệp nên dùng:

> Johnson cho thấy team có thể biến một hồ sơ BCQT phức tạp thành pipeline có kiểm soát, có audit, có truy vết và có validation. Từ kinh nghiệm đó, team có thể hỗ trợ HQ xây lớp sàng lọc rủi ro trên dữ liệu tờ khai và báo cáo BCQT đã nộp, rồi mở rộng sang kiểm tra sâu khi có dữ liệu doanh nghiệp cung cấp.
