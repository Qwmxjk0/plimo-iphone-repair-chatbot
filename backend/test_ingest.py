import unittest
from ingest import catalog_documents

class IngestTests(unittest.TestCase):
    def test_demo_only_with_explicit_option_and_label(self):
        rows=[{'id':'real','confirmed':True,'name':'จริง','description':'ข้อมูลร้าน'},
              {'id':'demo','confirmed':False,'demo':True,'name':'ตัวอย่าง','description':'สาธิต','price':3200},
              {'id':'pending','confirmed':False,'name':'รอข้อมูล'}]
        texts,sources=catalog_documents(rows)
        self.assertEqual(sources,['real.json'])
        texts,sources=catalog_documents(rows,include_demo=True)
        self.assertEqual(sources,['real.json','demo-demo.json'])
        self.assertIn('ไม่ใช่ราคาจริงของร้าน',texts[1])
        self.assertIn('3,200',texts[1])
        self.assertEqual(len(texts),2)

    def test_estimates_are_indexed_without_demo_opt_in(self):
        rows=[{'id':'estimate','confirmed':True,'demo':False,'price_status':'estimate','name':'หน้าจอ','description':'เปลี่ยนหน้าจอ','price':3200}]
        texts,sources=catalog_documents(rows)
        self.assertEqual(sources,['estimate.json'])
        self.assertIn('ราคาประเมินเบื้องต้นเริ่มต้น 3,200 บาท',texts[0])
        self.assertIn('คำที่ลูกค้าใช้: จอแตก',texts[0])
        self.assertNotIn('ต้องบอกว่าเป็นราคาสาธิต',texts[0])
        # Shared approval policy lives once in shop.md, not repeated in every item chunk.
        self.assertNotIn('อนุมัติ',texts[0])

    def test_base_model_items_say_pro_is_separate(self):
        rows=[{'id':'b','confirmed':True,'name':'เปลี่ยนแบตเตอรี่ iPhone 11–13','description':'เปลี่ยนแบต','price':990,'models':['iPhone 11','iPhone 12','iPhone 13']},
              {'id':'p','confirmed':True,'name':'เปลี่ยนชุดลำโพง','description':'ลำโพง','price':890,'models':['iPhone 11–17 รวม Pro / Pro Max']}]
        texts,_=catalog_documents(rows)
        self.assertIn('ไม่รวม Pro / Pro Max',texts[0]); self.assertNotIn('ไม่รวม',texts[1])

    def test_markdown_split_by_section(self):
        from ingest import markdown_sections
        texts,sources=markdown_sections('# ร้าน\nเวลาเปิด 10:00\n## ราคา\nราคาเบื้องต้น\n## ชำระเงิน\nปุ่มในบัญชี','shop.md')
        self.assertEqual(sources,['shop-1.md','shop-2.md','shop-3.md'])
        self.assertTrue(all(t.startswith('# ร้าน') for t in texts)); self.assertIn('ปุ่มในบัญชี',texts[2])

if __name__=='__main__':unittest.main()
