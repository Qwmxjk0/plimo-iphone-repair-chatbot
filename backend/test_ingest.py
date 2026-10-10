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
        self.assertIn('3200',texts[1])
        self.assertEqual(len(texts),2)

    def test_estimates_are_indexed_without_demo_opt_in(self):
        rows=[{'id':'estimate','confirmed':True,'demo':False,'price_status':'estimate','name':'หน้าจอ','description':'เปลี่ยนหน้าจอ','price':3200}]
        texts,sources=catalog_documents(rows)
        self.assertEqual(sources,['estimate.json'])
        self.assertIn('ราคาประเมินเบื้องต้น',texts[0])
        self.assertIn('อนุมัติ',texts[0])
        self.assertNotIn('ต้องบอกว่าเป็นราคาสาธิต',texts[0])

if __name__=='__main__':unittest.main()
